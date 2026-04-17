import pandas as pd 
import os
from tqdm import tqdm

if __name__ == "__main__":
    CURRENT_PATH = os.path.dirname(__file__)
    DATA_PATH = os.path.join(CURRENT_PATH, "data")
    
    # Load the manual correction data
    manual_correction_path = os.path.join(DATA_PATH, "Mislocated_installations.xlsx")
    manual_correction_df = pd.read_excel(manual_correction_path, sheet_name="Sheet1", engine="openpyxl")
    
    manual_corrected_coordinates = {}
    for row in tqdm(manual_correction_df.to_dict('records')):
        installation_id = row["installation_id"]
        latitude = row["lat"]
        longitude = row["lon"]
        
        manual_corrected_coordinates[installation_id] = (latitude, longitude)
        
        
    # Load the latest computed coordinates
    latest_coordinates_path = os.path.join(DATA_PATH, "eutl_installations-output.csv")
    latest_coordinates_df = pd.read_csv(latest_coordinates_path)
    
    merged_rows = []
    for row in tqdm(latest_coordinates_df.to_dict('records')):
        installation_id = row["installation_id"]
        
        if not installation_id in manual_corrected_coordinates:
            merged_rows.append(row)
        else:
            lat, lon = manual_corrected_coordinates[installation_id]
            merged_rows.append({
                **row,
                "lat": lat,
                "lon": lon
            })
            
    merged_df = pd.DataFrame(merged_rows)
    merged_df.to_csv(os.path.join(DATA_PATH, "eutl_installations_with_manual_correction_coordinates.csv"), index=False)

   