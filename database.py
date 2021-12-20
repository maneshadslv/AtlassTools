import sqlite3

conn = sqlite3.connect('C:\\AtlassTools\\test\\test.db')

c = conn.cursor() # The database will be saved in the location where your 'py' file is saved

# Create table - CLIENTS
c.execute('''CREATE TABLE CLIENTS
             ([generated_id] INTEGER PRIMARY KEY,[Client_Name] text, [Country_ID] integer, [Date] date)''')
          
# Create table - COUNTRY
c.execute('''CREATE TABLE COUNTRY
             ([generated_id] INTEGER PRIMARY KEY,[Country_ID] integer, [Country_Name] text)''')
        
# Create table - DAILY_STATUS
c.execute('''CREATE TABLE DAILY_STATUS
             ([Client_Name] text, [Country_Name] text, [Date] date)''')
                 
conn.commit()
