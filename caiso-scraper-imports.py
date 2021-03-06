#!/usr/bin/env python3
#don't know what that means, but there it is

#DOWNLOADS DAILY 5-MIN IMPORT DATA FOR A SPECIFIED DATE RANGE FROM CAISO'S "TODAY'S OUTLOOK" PAGE.
#SAVES TO path/CAISOcsv/Results, WHERE "path" IS THE DIRECTORY WHERE THIS FILE IS SAVED

#must have chromedriver installed here: '/usr/local/bin/chromedriver' (or change line 85 to the correct directory for chromedriver)
#must have the imported libraries below installed

#example command line:
#cd /Users/kajpeterson/Desktop/Desktop/Python/CAISO
#python3 caiso-scraper-imports.py imports_test10-12.csv 3 10 2020 3 12 2020
#as of 3/4/2020, the earliest available data is from 4/10/2018.

#TODO:
#add code to check for error messages on CAISO's page
#add to code to check for blank values with non-blank timestamps

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import datetime
import os
import glob
import pandas as pd
import csv
import shutil
import time
import sys
import numpy as np

#just curious how long it takes to run. 
tic = time.time()

#INPUTS
filename = sys.argv[1]
startdate = datetime.date(int(sys.argv[4]),int(sys.argv[2]),int(sys.argv[3]))
enddate = datetime.date(int(sys.argv[7]),int(sys.argv[5]),int(sys.argv[6]))
date = startdate

#=================================================================================
#SETUP DIRECTORIES AND CHROMEDRIVER

#Make CAISOcsv & Results folders if they don't already exist
#Clear and make temporary directories for downloads and intermediary transposed csv's
#TempDir1 for downloads, TempDir2 for intermiediary transposed csv's, Results for final csv's:
path = sys.path[0]
CAISOcsv_path = f'{path}/CAISOcsv/'
Results_path = f'{path}/CAISOcsv/Results/'
TempDir1_path = f'{path}/CAISOcsv/TempDir1/'
TempDir2_path = f'{path}/CAISOcsv/TempDir2/'

try:
    os.mkdir(CAISOcsv_path)
    print("made new CAISOcsv folder")
except FileExistsError:
    pass

try:
    os.mkdir(Results_path)
    print("made new Results folder")
except FileExistsError:
    pass

try:
    os.mkdir(TempDir1_path)
except FileExistsError:
    try:
        shutil.rmtree(TempDir1_path)
        os.mkdir(TempDir1_path)
        print("made new TempDir1")
    except OSError as e:
        print("Error: %s : %s" %(TempDir1_path, e.strerror))

try:
    os.mkdir(TempDir2_path)
except FileExistsError:
    try:
        shutil.rmtree(TempDir2_path)
        os.mkdir(TempDir2_path)
        print("made new TempDir2")
    except OSError as e:
        print("Error: %s : %s" %(TempDir2_path, e.strerror))

#initiate chromedriver, set download directory to TempDir1, make headless, get CAISO page.
chromedriver = '/usr/local/bin/chromedriver'
options = webdriver.ChromeOptions()
prefs = {"download.default_directory" : TempDir1_path}
options.add_experimental_option("prefs",prefs)
options.add_argument('headless')
browser = webdriver.Chrome(executable_path=chromedriver, chrome_options=options) 
browser.get('http://www.caiso.com/TodaysOutlook/Pages/supply.aspx')

#=================================================================================
#DOWNLOADER

#finds date input element
elements = browser.find_elements_by_tag_name('input')
for element in elements:
    if 'imports-date' in element.get_attribute('class'):       
        
        #Enters date
        while date <= enddate:
            element.click()
            element.clear()
            date_input = (date.strftime("%m/%d/%Y"))
            element.send_keys(date_input)
            element.send_keys(Keys.ENTER)
            
            #Clicks download link
            button1 = browser.find_element_by_xpath('//*[@id="dropdownMenuImports"]')
            time.sleep(1.5)       #make sure it has time to load. Otherwise, there can be missing values or duplicates. I TRIED CHANGING 1.5 TO 2, BUT IT DIDN'T REDUCE DUPLICATES.
            button1.click()
            button2 = browser.find_element_by_xpath('//*[@id="downloadImportsCSV"]')
            
            #in case the browser is lagging, it will keep trying to click the link
            while True:
                try:
                    button2.click()
                    print("downloading", date_input)
                except:     #add specific exceptions?
                    time.sleep(0.5)
                    print("needed a nap")
                    continue
                break
            date = date + datetime.timedelta(1)

#kill invisiable headless browser
browser.close()

#=================================================================================
#FORMAT DAILY DATA

#grabbing csv's from TempDir1, transposing, stripping headings, adding date column
os.chdir(TempDir1_path)
extension = 'csv'
all_filenames = [i for i in glob.glob('*.{}'.format(extension))]            
print("{} files in all_filenames".format(len(all_filenames)))
print("formatting data...")
missing_data_log = []

for f in range(0,len(all_filenames)):
    data = pd.read_csv(TempDir1_path+all_filenames[f], header=None)
    date = (data[0][0])
    print("formatting", date)
    
    #transpose & strip headings
    df = data.T
    df = df.iloc[1:]
    date_column = [date]*len(df)
    
    #flag dates with missing data
    if len(df) != 288:
        print("warning: {} has {} elements".format(date,len(df)))
        missing_data_log.append(date)
    
    #add date column & save csv to TempDir2
    df.insert(0,"date", date_column,True)  
    df.to_csv(TempDir2_path+all_filenames[f])    

#=================================================================================
#CONCATENATOR+SORTER

os.chdir(TempDir2_path)
day_filenames = [i for i in glob.glob('*.{}'.format(extension))]

#combine all files in the list
print("concatenating...")
combined_csv = pd.concat([pd.read_csv(f) for f in day_filenames])
combined_csv.columns = ["Datetime", "Date", "Time", "Imports"]

#create datetime object for sorting
print("combined_csv")
combined_csv.to_csv(TempDir2_path+'combined_csv.csv')
print("saved combined csv")

#Add datetime column
#I added Try/Except because one value in CAISO's import data was missing a timestamp, which caused an error when I tried to strip the time, but it was still able to make a datetime object without stripping.
print("adding datetime for sorting...")
df = pd.read_csv('/Users/kajpeterson/Desktop/Desktop/Python/CAISO/CAISOcsv/TempDir2/combined_csv.csv')
df = df.drop('Unnamed: 0',axis=1)
date_error_counter = 0
time_error_counter = 0
for index,row in df.iterrows():
    try:
        DATE = df.loc[index,'Date'].strip()
    except Exception as e:
        date_message = str(e)
        print (f"Failed to strip Date for index: {index}, row: {row}. Error message: {date_message}")
        date_error_counter += 1
    try:
        TIME = df.loc[index,'Time'].strip()
    except Exception as e:
        time_message = str(e)
        print (f"Failed to strip Time for index: {index}, row: {row}. Error message: {time_message}")
        time_error_counter += 1
    df.loc[index,'Datetime'] = datetime.datetime.combine(datetime.datetime.strptime(DATE, '%m/%d/%Y') ,datetime.datetime.strptime(TIME,'%H:%M').time())
try:
    print (f"Failed to strip Date for {date_error_counter} rows. Error message: {date_message}")
except:
    pass
try:
    print (f"Failed to strip Time for {time_error_counter} rows. Error message: {time_message}")
except:
    pass

#sort by datetime
print("sorting")
final_df = df.sort_values(by='Datetime')

#=================================================================================
#REPORT + SAVE

#report missing data
print("-------------------------")
print("dates queried:", enddate - startdate + datetime.timedelta(1))
print("dates returned:", len(all_filenames))
print("Given dates returned:")
print("  values expected:", 288*len(all_filenames))
print("  values returned:", len(final_df))
print("dates with missing data:", missing_data_log)
#print("dates with duplicate data:", duplicate_data_log)
print("-------------------------")

#save to Results folder
final_df.to_csv(Results_path+filename)
print("saved final csv")

#=================================================================================
#DUPLICATE CHECK

print("checking for duplicates...")
df = pd.read_csv('/Users/kajpeterson/Desktop/Desktop/Python/CAISO/CAISOcsv/Results/'+filename)
df['Date'] = df['Date'].str.strip()
df.set_index("Date", inplace=True)
df.head()
date = startdate
duplicate_data_log = []
previous = []
notfirstday = 0
while date <= enddate:
    date_input = (date.strftime("%m/%d/%Y"))
    elements = df.loc[[date_input],["Imports"]]
    if notfirstday == 0:
        pass
    elif np.array_equal(elements.values,previous.values):
        print("warning: {} is a duplicate of the previous date".format(date_input))
        duplicate_data_log.append(date_input)
    previous = elements
    date = date + datetime.timedelta(1)
    notfirstday = 1
print("duplicate_data_log:",duplicate_data_log)
toc = time.time()
print(toc-tic,'seconds elapsed')
print("DONE")

quit()
