import googlemaps
from pprint import pprint
import pandas as pd
import time
from bs4 import BeautifulSoup

file = open("../Google Maps API.txt", "r") # Txt containing Google Maps API key
api_key = file.read()
file.close()

gmaps = googlemaps.Client(key = api_key)

def find_police(gps_location):
    
    radius_km = 6 
    final_radius_km = 20

    police_stations = gmaps.places_nearby(location = gps_location, keyword = 'police station', type = 'police', radius = radius_km*1000)
    
    while police_stations["status"] == 'ZERO_RESULTS':
        radius_km += 2
        print(f"No Police Stations Found. Extending radius to {radius_km} kms....")
        police_stations = gmaps.places_nearby(location = gps_location, keyword = 'police station', type = 'police', radius = radius_km*1000)
        if radius_km == final_radius_km:
            print(f"No Police Stations found within {final_radius_km} kms")
            return None, None, None
    
    return radius_km, police_stations, len(police_stations["results"])

def sort_police_stations(optimum_police_stations):
    
    optimum_police_stations["Duration"] = optimum_police_stations["Duration"].apply(lambda x: int(x.split(' ')[0]) if 'mins' in x else None)
    optimum_police_stations = optimum_police_stations.sort_values(by = ['Duration', 'Total Ratings'], ascending = [True, False], ignore_index = True)
    optimum_police_stations["Duration"] = optimum_police_stations["Duration"].apply(lambda x: str(x) + ' mins' if x is not None else None)

    return optimum_police_stations

# Main
def find_optimum_police(gps_location, show_info = True, show_directions = True):

    time_of_accident = time.strftime("%H:%M:%S", time.localtime(time.time()))
    radius, police_stations, n = find_police(gps_location)

    optimum_police_stations = pd.DataFrame(columns = ['Place ID', 'Police Name', 'Total Ratings', 'Distance', 'Duration', 'Duration in secs'])
    police_data = []

    if police_stations:
        for police_station in police_stations["results"]:
            # Distance from Accident Location -> Police Station
            distance = gmaps.distance_matrix(origins = gps_location, 
                                            destinations = "place_id:" + police_station["place_id"], 
                                            mode = "driving",
                                            departure_time = time.time(),
                                            traffic_model = "best_guess",
                                            units = "metric")
            
            gps_location_address = distance['origin_addresses'][0]
            
            police_data.append({'Place ID': police_station["place_id"], 
                        'Police Name': police_station["name"],
                        'Address': distance["destination_addresses"][0],
                        'Total Ratings': police_station["user_ratings_total"] if "user_ratings_total" in police_station else 0,
                        'Map Link' : f"https://www.google.com/maps/place/?q=place_id:{police_station['place_id']}",
                        'Distance': distance["rows"][0]["elements"][0]["distance"]["text"] if 'OK' in distance["status"] else None, 
                        'Mode of Transportation' : "Driving",
                        'Duration': distance["rows"][0]["elements"][0]["duration_in_traffic"]["text"] if 'OK' in distance["status"] else None, 
                        'Duration in secs' : distance["rows"][0]["elements"][0]["duration_in_traffic"]["value"] if 'OK' in distance["status"] else None})
            
            optimum_police_stations = optimum_police_stations.from_records(police_data)
        
        police_data.clear()
        
        optimum_police_stations  = sort_police_stations(optimum_police_stations) # Sorting wrt duration in mins
        # optimum_police_stations = optimum_police_stations.sort_values(by = ['Duration in secs', 'Total Ratings'], ascending = [True, False], ignore_index = True)  # Sorting wrt duration in secs
        
        most_optimum_police_station_index = None
        for _index in range(len(optimum_police_stations)):
            contact = gmaps.place(place_id = optimum_police_stations.iloc[_index]["Place ID"],
                            fields = ['formatted_phone_number'])
            if "formatted_phone_number" in contact["result"]:
                most_optimum_police_station_index = _index
                most_optimum_police_station_contact = contact["result"]["formatted_phone_number"].replace(" ", "")
                break
        
        if show_info:
            print(f"{n} Police Station(s) found within {radius} kms!", end = '\n\n')
            print("------------------- Accident Location -------------------", end = '\n\n')
            print(f'Address: {gps_location_address}')
            print("Coordinates:", gps_location)
            print("Time of Detected Accident:", time_of_accident, end = '\n'*2)

            if most_optimum_police_station_index is not None:
                for i in range(most_optimum_police_station_index + 1):
                    if i != most_optimum_police_station_index:
                        print(f"No Contact Number found for '{optimum_police_stations.iloc[i]['Police Name']}'. Skipping to next nearest...", end = '\n\n')
                    else:
                        print(f'----------------------- Police Station within the quickest reach ({_index}) -----------------------', end = '\n\n')
                        print("\n".join(f"{key:<25}: {value}" for key, value in optimum_police_stations.iloc[i].items()))
                        print()
                        print("Contact Number:", most_optimum_police_station_contact)

                        if show_directions:
                            # Directions from Accident Location -> Police Station 
                            most_optimum_police_station = optimum_police_stations.iloc[i]
                            directions = gmaps.directions(origin = gps_location, 
                                                    destination = f"place_id:{most_optimum_police_station['Place ID']}", 
                                                    mode = "driving",
                                                    departure_time = time.time(),
                                                    traffic_model = "best_guess",
                                                    units = "metric")
                            
                            print()
                            print("Directions from Accident Location -> Police Station:", end = '\n\n')
                            
                            for index, direction in enumerate(directions[0]["legs"][0]["steps"]):
                                soup = BeautifulSoup(direction['html_instructions'], 'html.parser')
                                directions_text = soup.get_text()
                                print(f'Step {index + 1}: {directions_text}')   

                        
                            # Directions from Police Station -> Accident Location
                            directions = gmaps.directions(origin = f"place_id:{most_optimum_police_station['Place ID']}", 
                                                    destination = gps_location,
                                                    mode = "driving",
                                                    departure_time = time.time(),
                                                    traffic_model = "best_guess",
                                                    units = "metric")
                            
                            print('\n')
                            print("----------------- Directions from Police Station -> Accident Location -----------------", end = '\n\n')
                            print(f"Distance: {directions[0]['legs'][0]['distance']['text']}")
                            print("Mode of Transportation: Driving")
                            print(f"Duration: {directions[0]['legs'][0]['duration_in_traffic']['text']}", end = "\n\n")
                            
                            for index, direction in enumerate(directions[0]["legs"][0]["steps"]):
                                soup = BeautifulSoup(direction['html_instructions'], 'html.parser')
                                directions_text = soup.get_text()
                                print(f'Step {index + 1}: {directions_text}')
            else:
                most_optimum_police_station_contact = None
                print("No contant information found for any of the police stations.")
                print(f'----------------------- Police Station within the quickest reach ({_index}) -----------------------', end = '\n\n')
                print("\n".join(f"{key:<25}: {value}" for key, value in optimum_police_stations.iloc[0].items()))
        
    return optimum_police_stations.iloc[most_optimum_police_station_index], most_optimum_police_station_contact

if __name__ == '__main__':
    
    gps_location = () # (Lat, Lng) - Fetched From a GPS Module (CCTV camera should be equipped with a GPS module)
    x, y = find_optimum_police(gps_location, show_info = True, show_directions = True)
