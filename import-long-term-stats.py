import sqlite3
import argparse
import sys


def get_example_value(source_cur, metadata_id):
    source_cur.execute("""
        SELECT s.state, s.mean, sm.unit_of_measurement 
        FROM statistics s
        JOIN statistics_meta sm ON s.metadata_id = sm.id
        WHERE s.metadata_id = ?
        ORDER BY s.created DESC
        LIMIT 1
    """, (metadata_id,))
    row = source_cur.fetchone()
    if row:
        value = row[0] if row[0] is not None else row[1]
        unit = row[2] if row[2] else "unknown unit"
        return f"{value} {unit}"
    return "No recent value found"


def verify_name_in_target(target_cur, name):
    target_cur.execute("SELECT id FROM statistics_meta WHERE statistic_id = ?", (name,))
    return target_cur.fetchone() is not None

def import_statistics(source_db, target_db, batch_size=1000, dry_run=False):
    # Connect to both databases
    source_conn = sqlite3.connect(source_db)
    target_conn = sqlite3.connect(target_db)
    
    source_cur = source_conn.cursor()
    target_cur = target_conn.cursor()
    
    # Create a mapping of metadata_id to statistic_id in the source database
    source_cur.execute("SELECT id, statistic_id FROM statistics_meta")
    source_metadata = {row[0]: row[1] for row in source_cur.fetchall()}
    
    # Create a mapping of statistic_id to metadata_id in the target database
    target_cur.execute("SELECT id, statistic_id FROM statistics_meta")
    target_metadata = {row[1]: row[0] for row in target_cur.fetchall()}
    
    # Prepare the insert statement
    column_names = ['id', 'created', 'metadata_id', 'start', 'mean', 'min', 'max', 'last_reset', 'state', 'sum', 'created_ts', 'start_ts', 'last_reset_ts']
    
    # Process rows in batches
    skip_all = set()
    source_metadata_not_found = set()
    missing_source_ids = set()
    name_mappings = {}

    for table_name in ('statistics_short_term', 'statistics'):
        insert_sql = f"""
        INSERT OR REPLACE INTO {table_name} 
        ({", ".join(column_names)})
        VALUES ({"?, " * (len(column_names) - 1) + "?"})
        """
        # Get the total number of rows
        source_cur.execute(f"SELECT COUNT(*) FROM {table_name}")
        total_rows = source_cur.fetchone()[0]
        
        offset = 0
        rows_to_insert = 0
        rows_skipped = 0
        print(f"Processing '{table_name}' table...")
        while True:
            source_cur.execute(f"SELECT {', '.join(column_names)} FROM {table_name} LIMIT {batch_size} OFFSET {offset}")
            rows = source_cur.fetchall()
            
            if not rows:
                break

            # Process each row
            for row in rows:
                # Get the name corresponding to the metadata_id in the source database
                source_name = source_metadata.get(row[2])
                
                if source_name:
                    # Look up the corresponding metadata_id in the target database
                    target_metadata_id = target_metadata.get(source_name)
                    
                    
                    if not target_metadata_id:
                        if source_name in name_mappings:
                            new_name = name_mappings[source_name]
                            target_metadata_id = target_metadata.get(new_name)
                        elif source_name not in skip_all:
                            missing_source_ids.add(row[2])
                            example_value = get_example_value(source_cur, row[2])
                            print(f"\nMissing metadata in target for: {source_name}")
                            print(f"Most recent value: {example_value}")
                            while True:
                                prompt = "Choose action [1-3] where 1=Skip  2=Skip all  3=Provide new entity ID: "
                                action = None
                                if dry_run:
                                    print(prompt + "2")
                                    action = '2'
                                else:
                                    action = input(prompt).lower().strip()
                                if action == '1':
                                    break
                                elif action == '2':
                                    skip_all.add(source_name)
                                    break
                                elif action == '3':
                                    while True:
                                        new_name = input("Enter new entity ID: ").strip()
                                        if verify_name_in_target(target_cur, new_name):
                                            name_mappings[source_name] = new_name
                                            target_metadata_id = target_metadata.get(new_name)
                                            break
                                        else:
                                            print(f"'{new_name}' not found in target database. Please try again.")
                                            break
                                    break
                                else:
                                    print("Invalid action. Please try again.")

                    if target_metadata_id:
                        # Create a new row with the updated metadata_id
                        new_row = list(row)
                        new_row[2] = target_metadata_id
                        if not dry_run:
                            target_cur.execute(insert_sql, new_row)
                        rows_to_insert += 1
                    else:
                        rows_skipped += 1

                else:
                    if row[2] not in source_metadata_not_found:
                        print(f"Warning: No metadata found in source for id: {row[2]}. Ignoring all")
                        source_metadata_not_found.add(row[2])

            if not dry_run:
                target_conn.commit()
            offset += batch_size
            if offset % (batch_size * 10) == 0:
                print(f"Processed {min(offset, total_rows)} out of {total_rows} rows")


        print(f"\nSummary for {table_name}:")
        print(f"Total rows processed: {total_rows}")
        print(f"Rows to be inserted: {rows_to_insert}")
        print(f"Rows skipped: {rows_skipped}")
    if dry_run:
        print("This was a dry run. No changes were made to the target database.")
        print("\nThe following entities were not found in the target database during the dry run:")
        for id in missing_source_ids:
            example_value = get_example_value(source_cur, id)
            print(f"{source_metadata[id]} ({example_value})")
    # Commit changes and close connections
    source_conn.close()
    target_conn.close()

def main():
    parser = argparse.ArgumentParser(description='Import statistics from source database to target database.')
    parser.add_argument('source_db', help='Path to the source database file')
    parser.add_argument('target_db', help='Path to the target database file')
    parser.add_argument('--batch-size', type=int, default=1000, help='Number of rows to process in each batch')
    parser.add_argument('--dry-run', action='store_true', help='Perform a dry run without modifying the target database')

    args = parser.parse_args()
    
    print(f"Importing from {args.source_db} to {args.target_db}")
    import_statistics(args.source_db, args.target_db, args.batch_size, args.dry_run)
    print("Import completed.")

if __name__ == "__main__":
    main()
