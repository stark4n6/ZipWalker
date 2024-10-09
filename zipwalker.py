import datetime
import zipfile
import struct
import argparse
import os
import sqlite3

def decode_extended_timestamp(extra_data):
    offset = 0
    length = len(extra_data)
    while offset < length:
        header_id, data_size = struct.unpack_from('<HH', extra_data, offset)
        offset += 4
        if header_id == 0x5455:  # Extended Timestamp Extra Field
            flags = struct.unpack_from('B', extra_data, offset)[0]
            offset += 1
            timestamps = {}
            if flags & 1:  # Modification time
                mtime, = struct.unpack_from('<I', extra_data, offset)
                timestamps['mtime'] = datetime.datetime.fromtimestamp(mtime, datetime.timezone.utc)
                offset += 4
            if flags & 2:  # Access time
                atime, = struct.unpack_from('<I', extra_data, offset)
                timestamps['atime'] = datetime.datetime.fromtimestamp(atime, datetime.timezone.utc)
                offset += 4
            if flags & 4:  # Creation time
                ctime, = struct.unpack_from('<I', extra_data, offset)
                timestamps['ctime'] = datetime.datetime.fromtimestamp(ctime, datetime.timezone.utc)
                offset += 4
            return timestamps
        else:
            offset += data_size
    return None

def main(zip_path,db_file_path):
    try:
        with zipfile.ZipFile(zip_path, mode="r") as archive, sqlite3.connect(db_file_path) as conn:
            cursor = conn.cursor()

            # Create a table to store the paths with created, modified dates, file name, and extension
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS file_listing (
                    file_name TEXT,
                    file_extension TEXT,
                    path TEXT PRIMARY KEY,
                    created_date TEXT,
                    modified_date TEXT,
                    accessed_date TEXT,
                    is_file INTEGER,
                    size INTEGER,
                    comp_size INTEGER
                )
            ''')

            for info in archive.infolist():
                path = info.filename
                #info = archive.getinfo(target_filename)
                
                size = info.file_size
                comp_size = info.compress_size

                #print(f"Modified: {datetime.datetime(*info.date_time)}")
                
                timestamps = decode_extended_timestamp(info.extra)
                if timestamps and 'ctime' in timestamps:
                    created_date = timestamps['ctime']
                else:
                    created_date = 'N/A'
                if timestamps and 'atime' in timestamps:
                    accessed_date = timestamps['atime']
                else:
                    accessed_date = 'N/A'
                if timestamps and 'mtime' in timestamps:
                    modified_date = timestamps['mtime']
                else:
                    modified_date = 'N/A'            
                
                is_file = 1 if not path.endswith('/') else 0  # Check if it's a file
                file_name = os.path.basename(path) if is_file else None
                file_extension = os.path.splitext(file_name)[1] if is_file else None
                
                cursor.execute("INSERT INTO file_listing (file_name, file_extension, path, created_date, modified_date, accessed_date, is_file, size, comp_size) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                           (file_name, file_extension, path, created_date, modified_date, accessed_date, is_file, size, comp_size))

        conn.commit()

    except FileNotFoundError:
        print(f"ZIP file '{zip_path}' not found.")
        
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract and print file timestamps from a ZIP archive.")
    parser.add_argument("zip_path", help="Path to the ZIP file")
    parser.add_argument("export_path", help="Path for the export report")
    args = parser.parse_args()
    main(args.zip_path,args.export_path+'\file_listing.db')