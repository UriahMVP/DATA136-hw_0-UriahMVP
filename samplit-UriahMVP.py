# This comment resolves the merging conflict
import sys
import random

file_path = sys.argv[1]
    
with open(file_path, 'r') as file:
    header = next(file)  
    print(header, end='') 
    for line in file:
        if random.random() < 0.01:
            print(line, end='')
