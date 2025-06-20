import sqlite3
import csv


def export_simulation_to_csv(sim_id, output_path="simulation_export.csv", db_path="collisions.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    with open(output_path, mode='w', newline='') as file:
        writer = csv.writer(file)

        # 1. Export project metadata
        writer.writerow(["=== Project Metadata ==="])
        cursor.execute("SELECT simulation_id, name, timestamp FROM projects WHERE simulation_id = ?", (sim_id,))
        project_row = cursor.fetchone()
        if project_row:
            writer.writerow(["simulation_id", "name", "timestamp"])
            writer.writerow(project_row)
        else:
            writer.writerow(["No project found for simulation_id =", sim_id])

        writer.writerow([])

        # 2. Export shape metadata
        writer.writerow(["=== Shape Metadata ==="])
        cursor.execute("""
            SELECT shape_id, name, coords, count, collectarea, percentofstrikes, kdtreepath 
            FROM shape_metadata 
            WHERE simulation_id = ?
        """, (sim_id,))
        shape_rows = cursor.fetchall()
        if shape_rows:
            writer.writerow(["shape_id", "name", "coords", "count", "collectarea", "percentofstrikes", "kdtreepath"])
            for row in shape_rows:
                writer.writerow(row)
        else:
            writer.writerow(["No shape metadata found for simulation_id =", sim_id])

        writer.writerow([])

        # 3. Export collision information
        writer.writerow(["=== Collision Records ==="])
        cursor.execute("""
            SELECT center_on_contact, surface_on_contact, peakcurrent, strike, structurestruck, count 
            FROM collisions 
            WHERE simulation_id = ?
        """, (sim_id,))
        collision_rows = cursor.fetchall()
        if collision_rows:
            writer.writerow(["center_on_contact", "surface_on_contact", "peakcurrent", "strike", "structurestruck", "count"])
            for row in collision_rows:
                writer.writerow(row)
        else:
            writer.writerow(["No collisions found for simulation_id =", sim_id])

    conn.close()
    print(f"Simulation {sim_id} exported successfully to '{output_path}'")






def import_simulation_from_csv(csv_path, db_path="collisions.db"):
    with open(csv_path, newline='') as file:
        reader = csv.reader(file)
        rows = list(reader)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # STEP 1: Extract and insert project metadata (with new sim_id)
    try:
        project_start = rows.index(["=== Project Metadata ==="])
        shape_start = rows.index(["=== Shape Metadata ==="])
        collision_start = rows.index(["=== Collision Records ==="])
    except ValueError as e:
        print("Invalid CSV format:", e)
        return

    # Get project metadata row
    project_data = rows[project_start + 2]  # Skip header
    project_name = project_data[1] + " (imported)"

    # Insert project to get new simulation_id
    cursor.execute("INSERT INTO projects (name) VALUES (?)", (project_name,))
    new_sim_id = cursor.lastrowid
    print(f"New simulation ID: {new_sim_id}")

    # STEP 2: Insert shape metadata
    shape_header_row = shape_start + 1
    for row in rows[shape_header_row + 1:collision_start - 1]:
        if not row or row[0].startswith("==="): break  # stop at next section or end
        cursor.execute("""
            INSERT INTO shape_metadata (
                simulation_id, shape_id, name, coords, count, collectarea, percentofstrikes, kdtreepath
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (new_sim_id, *row))

    # STEP 3: Insert collision records
    collision_header_row = collision_start + 1
    for row in rows[collision_header_row + 1:]:
        if not row or row[0].startswith("==="): break
        cursor.execute("""
            INSERT INTO collisions (
                center_on_contact, surface_on_contact, peakcurrent, strike, structurestruck, count, simulation_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (*row, new_sim_id))

    conn.commit()
    conn.close()
    print(f"Successfully imported simulation from '{csv_path}' with new ID {new_sim_id}")