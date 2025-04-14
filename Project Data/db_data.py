import sqlite3

# Connect to the SQLite database
conn = sqlite3.connect('mydb.db')
cursor = conn.cursor()

# Get column names for a specific table
cursor.execute("PRAGMA table_info(users);")

# Fetch the result
columns = cursor.fetchall()

# Extract and print column names
column_names = [column[1] for column in columns]
print(column_names)

# Close the connection
conn.close()
