import random
import math
import time
import threading
import pygame
import sys
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.backends.backend_agg as agg
import numpy as np
from io import BytesIO
import pygame.freetype

# Add pygame mixer for audio
pygame.mixer.init()

# Constants for signal timing
defaultRed = 150
defaultYellow = 5
defaultGreen = 20
defaultMinimum = 10
defaultMaximum = 60

# Global variables
signals = []
noOfSignals = 4
simTime = 300
timeElapsed = 0

currentGreen = 0
nextGreen = (currentGreen+1)%noOfSignals
currentYellow = 0

# Add fuel emission tracking variables
total_fuel_saved = 0
total_co2_reduction = 0
fuel_saved_per_vehicle = 0.02  # Liters per minute of waiting time reduced
co2_per_liter = 2.3  # kg of CO2 per liter of fuel
avg_wait_time_reduction = 0.2  
# Vehicle timing constants
carTime = 2
bikeTime = 1
rickshawTime = 2.25 
busTime = 2.5
truckTime = 2.5
ambulanceTime = 1

# Vehicle counters
noOfCars = 0
noOfBikes = 0
noOfBuses =0
noOfTrucks = 0
noOfRickshaws = 0
noOfLanes = 2

detectionTime = 5

# Emergency vehicle variables
emergencyVehiclePresent = False
emergencyDirection = -1
emergencyLane = -1
emergencyOverride = False
emergencyTimer = 0
emergencyGreenTime = 15
emergencyVehicleCount = 0
emergencyPriorityActive = False
emergencyCooldown = 0
emergencyResponseTimes = []
emergencyArrivalTime = 0
emergencyPassageTime = 0
emergencyPassageAlert = False
emergencyAlertDuration = 5

# New variables for ambulance audio
ambulance_siren_playing = False
ambulance_siren = None

# Stats tracking
stats_data = {
    'time': [],
    'vehicles_passed': {
        'right': [],
        'down': [],
        'left': [],
        'up': []
    },
    'total_vehicles': [],
    'emergency_vehicles': [],
    'signal_times': {
        'right': {'green': [], 'red': [], 'yellow': []},
        'down': {'green': [], 'red': [], 'yellow': []},
        'left': {'green': [], 'red': [], 'yellow': []},
        'up': {'green': [], 'red': [], 'yellow': []}
    }
}

# Function to check for emergency vehicles
def checkEmergencyVehicles():
    global currentGreen, currentYellow, emergencyOverride, emergencyTimer, emergencyPriorityActive, emergencyCooldown, ambulance_siren_playing
    
    if emergencyCooldown > 0:
        emergencyCooldown -= 1
        return
    
    if emergencyVehiclePresent and not emergencyOverride and emergencyDirection >= 0:
        if currentGreen != emergencyDirection:
            print("\n*** EMERGENCY VEHICLE DETECTED IN RED SIGNAL LANE - CHANGING SIGNALS IMMEDIATELY ***\n")
            print("Emergency vehicle detected in direction:", directionNumbers[emergencyDirection])
            emergencyOverride = True
            emergencyPriorityActive = True
            emergencyTimer = emergencyGreenTime
            
            currentYellow = 1
            signals[currentGreen].green = 0
            signals[currentGreen].yellow = 1
            
            # Play ambulance siren
            if not ambulance_siren_playing and ambulance_siren:
                ambulance_siren.play(-1)  # Loop the siren
                ambulance_siren_playing = True
            
            print("\a\a\a EMERGENCY VEHICLE APPROACHING - ALL LANES STOPPING - CLEARING PATH \a\a\a")
            
# Function to handle emergency signals
def handleEmergencySignals():
    global currentGreen, currentYellow, nextGreen, emergencyTimer, emergencyOverride, emergencyPriorityActive, emergencyCooldown
    
    if emergencyOverride:
        if currentYellow == 1:
            return
        
        currentGreen = emergencyDirection
        nextGreen = (currentGreen+1)%noOfSignals
        currentYellow = 0
        
        for i in range(noOfSignals):
            if i != currentGreen:
                signals[i].red = emergencyGreenTime + 15
        
        signals[currentGreen].red = 0
        signals[currentGreen].yellow = 0
        signals[currentGreen].green = emergencyTimer
        
        emergencyTimer -= 1
        
        if emergencyTimer <= 0:
            emergencyOverride = False
            emergencyPriorityActive = False
            emergencyCooldown = 5
            signals[currentGreen].green = defaultGreen
            signals[currentGreen].yellow = defaultYellow
            signals[currentGreen].red = defaultRed
            
            print(f"Emergency vehicle has passed through intersection at time {timeElapsed}")

# Vehicle speeds
speeds = {'car':2.25, 'bus':1.8, 'truck':1.8, 'rickshaw':2, 'bike':2.5, 'ambulance':3.0}

# Coordinates
x = {'right':[0,0,0], 'down':[755,727,697], 'left':[1400,1400,1400], 'up':[602,627,657]}    
y = {'right':[348,370,398], 'down':[0,0,0], 'left':[498,466,436], 'up':[800,800,800]}

# Vehicle tracking
vehicles = {'right': {0:[], 1:[], 2:[], 'crossed':0}, 'down': {0:[], 1:[], 2:[], 'crossed':0}, 'left': {0:[], 1:[], 2:[], 'crossed':0}, 'up': {0:[], 1:[], 2:[], 'crossed':0}}
vehicleTypes = {0:'car', 1:'bus', 2:'truck', 3:'rickshaw', 4:'bike', 5:'ambulance'}
directionNumbers = {0:'right', 1:'down', 2:'left', 3:'up'}

# UI coordinates
signalCoods = [(530,230),(810,230),(810,570),(530,570)]
signalTimerCoods = [(530,210),(810,210),(810,550),(530,550)]
vehicleCountCoods = [(480,210),(880,210),(880,550),(480,550)]
vehicleCountTexts = ["0", "0", "0", "0"]

# Stop lines
stopLines = {'right': 590, 'down': 330, 'left': 800, 'up': 535}
defaultStop = {'right': 580, 'down': 320, 'left': 810, 'up': 545}
stops = {'right': [580,580,580], 'down': [320,320,320], 'left': [810,810,810], 'up': [545,545,545]}

# Intersection midpoints
mid = {'right': {'x':705, 'y':445}, 'down': {'x':695, 'y':450}, 'left': {'x':695, 'y':425}, 'up': {'x':695, 'y':400}}
rotationAngle = 3

# Spacing
gap = 15
gap2 = 15

# Initialize pygame
pygame.init()
simulation = pygame.sprite.Group()

# Traffic signal class
class TrafficSignal:
    def __init__(self, red, yellow, green, minimum, maximum):
        self.red = red
        self.yellow = yellow
        self.green = green
        self.minimum = minimum
        self.maximum = maximum
        self.signalText = "30"
        self.totalGreenTime = 0
        
# Vehicle class
class Vehicle(pygame.sprite.Sprite):
    def __init__(self, lane, vehicleClass, direction_number, direction, will_turn):
        pygame.sprite.Sprite.__init__(self)
        self.lane = lane
        self.vehicleClass = vehicleClass
        self.speed = speeds[vehicleClass]
        self.direction_number = direction_number
        self.direction = direction
        self.x = x[direction][lane]
        self.y = y[direction][lane]
        self.crossed = 0
        self.willTurn = will_turn
        self.turned = 0
        self.rotateAngle = 0
        self.isEmergency = (vehicleClass == 'ambulance')
        vehicles[direction][lane].append(self)
        self.index = len(vehicles[direction][lane]) - 1
        
        # Use absolute paths for image loading
        base_path = os.path.dirname(os.path.abspath(__file__))
        image_path = os.path.join(base_path, 'images', direction, f"{vehicleClass}.png")
        
        try:
            self.originalImage = pygame.image.load(image_path)
        except pygame.error:
            print(f"Warning: Could not load image {image_path}")
            # Create a placeholder image
            self.originalImage = pygame.Surface((40, 20))
            self.originalImage.fill((255, 0, 0) if self.isEmergency else (0, 0, 255))
        
        if vehicleClass == 'ambulance':
            try:
                car_path = os.path.join(base_path, 'images', direction, "car.png")
                car_image = pygame.image.load(car_path)
                car_width = car_image.get_rect().width
                car_height = car_image.get_rect().height
                self.originalImage = pygame.transform.scale(self.originalImage, (car_width, car_height))
            except pygame.error:
                pass
            
        self.currentImage = self.originalImage

        # Handle emergency vehicle detection
        if self.isEmergency and self.crossed == 0:
            global emergencyVehiclePresent, emergencyDirection, emergencyLane, emergencyArrivalTime, ambulance_siren_playing
            
            if not emergencyVehiclePresent:
                emergencyVehiclePresent = True
                emergencyDirection = direction_number
                emergencyLane = lane
                emergencyArrivalTime = timeElapsed
                
                # Play ambulance siren when detected
                if not ambulance_siren_playing and ambulance_siren:
                    ambulance_siren.play(-1)  # Loop the siren
                    ambulance_siren_playing = True
                
                print(f"\n*** NEW EMERGENCY VEHICLE DETECTED at time {timeElapsed} in {direction} direction ***\n")
    
        # Set vehicle position
        if(direction=='right'):
            if(len(vehicles[direction][lane])>1 and vehicles[direction][lane][self.index-1].crossed==0):
                self.stop = vehicles[direction][lane][self.index-1].stop - vehicles[direction][lane][self.index-1].currentImage.get_rect().width - gap
            else:
                self.stop = defaultStop[direction]
            temp = self.currentImage.get_rect().width + gap    
            x[direction][lane] -= temp
            stops[direction][lane] -= temp
        elif(direction=='left'):
            if(len(vehicles[direction][lane])>1 and vehicles[direction][lane][self.index-1].crossed==0):
                self.stop = vehicles[direction][lane][self.index-1].stop + vehicles[direction][lane][self.index-1].currentImage.get_rect().width + gap
            else:
                self.stop = defaultStop[direction]
            temp = self.currentImage.get_rect().width + gap
            x[direction][lane] += temp
            stops[direction][lane] += temp
        elif(direction=='down'):
            if(len(vehicles[direction][lane])>1 and vehicles[direction][lane][self.index-1].crossed==0):
                self.stop = vehicles[direction][lane][self.index-1].stop - vehicles[direction][lane][self.index-1].currentImage.get_rect().height - gap
            else:
                self.stop = defaultStop[direction]
            temp = self.currentImage.get_rect().height + gap
            y[direction][lane] -= temp
            stops[direction][lane] -= temp
        elif(direction=='up'):
            if(len(vehicles[direction][lane])>1 and vehicles[direction][lane][self.index-1].crossed==0):
                self.stop = vehicles[direction][lane][self.index-1].stop + vehicles[direction][lane][self.index-1].currentImage.get_rect().height + gap
            else:
                self.stop = defaultStop[direction]
            temp = self.currentImage.get_rect().height + gap
            y[direction][lane] += temp
            stops[direction][lane] += temp
        simulation.add(self)

    def render(self, screen):
        screen.blit(self.currentImage, (self.x, self.y))

    def move(self):
        global emergencyVehiclePresent, emergencyDirection, emergencyLane, emergencyOverride, emergencyVehicleCount
        global emergencyPassageAlert, emergencyPassageTime, emergencyPriorityActive, ambulance_siren_playing
        
        # Handle emergency vehicle passing through intersection
        if self.isEmergency and self.crossed == 1 and not hasattr(self, 'counted'):
            self.counted = True
            
            emergencyVehicleCount += 1
            
            emergencyPassageAlert = True
            emergencyPassageTime = timeElapsed
            
            # Stop the siren when the ambulance has passed
            if ambulance_siren_playing and ambulance_siren:
                ambulance_siren.fadeout(1000)  # Fade out over 1 second
                ambulance_siren_playing = False
            
            print(f"\n*** EMERGENCY VEHICLE PASSED THROUGH INTERSECTION at time {timeElapsed} ***\n")
            
            if emergencyDirection >= 0 and self.direction == directionNumbers[emergencyDirection]:
                emergencyVehiclePresent = False
                emergencyDirection = -1
                emergencyLane = -1
                emergencyOverride = False
                emergencyPriorityActive = False

        # Vehicle movement logic
        if(self.direction=='right'):
            if(self.crossed==0 and self.x+self.currentImage.get_rect().width>stopLines[self.direction]):
                self.crossed = 1
                vehicles[self.direction]['crossed'] += 1
            if(self.willTurn==1):
                if(self.crossed==0 or self.x+self.currentImage.get_rect().width<mid[self.direction]['x']):
                    if((self.x+self.currentImage.get_rect().width<=self.stop or (currentGreen==0 and currentYellow==0) or self.crossed==1 or self.isEmergency) and (self.index==0 or self.x+self.currentImage.get_rect().width<(vehicles[self.direction][self.lane][self.index-1].x - gap2) or vehicles[self.direction][self.lane][self.index-1].turned==1)):                
                        self.x += self.speed
                else:   
                    if(self.turned==0):
                        self.rotateAngle += rotationAngle
                        self.currentImage = pygame.transform.rotate(self.originalImage, -self.rotateAngle)
                        self.x += 2
                        self.y += 1.8
                        if(self.rotateAngle==90):
                            self.turned = 1
                    else:
                        if(self.index==0 or self.y+self.currentImage.get_rect().height<(vehicles[self.direction][self.lane][self.index-1].y - gap2) or self.x+self.currentImage.get_rect().width<(vehicles[self.direction][self.lane][self.index-1].x - gap2)):
                            self.y += self.speed
            else: 
                if((self.x+self.currentImage.get_rect().width<=self.stop or self.crossed == 1 or (currentGreen==0 and currentYellow==0) or self.isEmergency) and (self.index==0 or self.x+self.currentImage.get_rect().width<(vehicles[self.direction][self.lane][self.index-1].x - gap2) or (vehicles[self.direction][self.lane][self.index-1].turned==1))):                
                    self.x += self.speed

        elif(self.direction=='down'):
            if(self.crossed==0 and self.y+self.currentImage.get_rect().height>stopLines[self.direction]):
                self.crossed = 1
                vehicles[self.direction]['crossed'] += 1
            if(self.willTurn==1):
                if(self.crossed==0 or self.y+self.currentImage.get_rect().height<mid[self.direction]['y']):
                    if((self.y+self.currentImage.get_rect().height<=self.stop or (currentGreen==1 and currentYellow==0) or self.crossed==1 or self.isEmergency) and (self.index==0 or self.y+self.currentImage.get_rect().height<(vehicles[self.direction][self.lane][self.index-1].y - gap2) or vehicles[self.direction][self.lane][self.index-1].turned==1)):                
                        self.y += self.speed
                else:   
                    if(self.turned==0):
                        self.rotateAngle += rotationAngle
                        self.currentImage = pygame.transform.rotate(self.originalImage, -self.rotateAngle)
                        self.x -= 2.5
                        self.y += 2
                        if(self.rotateAngle==90):
                            self.turned = 1
                    else:
                        if(self.index==0 or self.x>(vehicles[self.direction][self.lane][self.index-1].x + vehicles[self.direction][self.lane][self.index-1].currentImage.get_rect().width + gap2) or self.y<(vehicles[self.direction][self.lane][self.index-1].y - gap2)):
                            self.x -= self.speed
            else: 
                if((self.y+self.currentImage.get_rect().height<=self.stop or self.crossed == 1 or (currentGreen==1 and currentYellow==0) or self.isEmergency) and (self.index==0 or self.y+self.currentImage.get_rect().height<(vehicles[self.direction][self.lane][self.index-1].y - gap2) or (vehicles[self.direction][self.lane][self.index-1].turned==1))):                
                    self.y += self.speed
            
        elif(self.direction=='left'):
            if(self.crossed==0 and self.x<stopLines[self.direction]):
                self.crossed = 1
                vehicles[self.direction]['crossed'] += 1
            if(self.willTurn==1):
                if(self.crossed==0 or self.x>mid[self.direction]['x']):
                    if((self.x>=self.stop or (currentGreen==2 and currentYellow==0) or self.crossed==1 or self.isEmergency) and (self.index==0 or self.x>(vehicles[self.direction][self.lane][self.index-1].x + vehicles[self.direction][self.lane][self.index-1].currentImage.get_rect().width + gap2) or vehicles[self.direction][self.lane][self.index-1].turned==1)):                
                        self.x -= self.speed
                else: 
                    if(self.turned==0):
                        self.rotateAngle += rotationAngle
                        self.currentImage = pygame.transform.rotate(self.originalImage, -self.rotateAngle)
                        self.x -= 1.8
                        self.y -= 2.5
                        if(self.rotateAngle==90):
                            self.turned = 1
                    else:
                        if(self.index==0 or self.y>(vehicles[self.direction][self.lane][self.index-1].y + vehicles[self.direction][self.lane][self.index-1].currentImage.get_rect().height +  gap2) or self.x>(vehicles[self.direction][self.lane][self.index-1].x + gap2)):
                            self.y -= self.speed
            else: 
                if((self.x>=self.stop or self.crossed == 1 or (currentGreen==2 and currentYellow==0) or self.isEmergency) and (self.index==0 or self.x>(vehicles[self.direction][self.lane][self.index-1].x + vehicles[self.direction][self.lane][self.index-1].currentImage.get_rect().width + gap2) or (vehicles[self.direction][self.lane][self.index-1].turned==1))):                
                    self.x -= self.speed
            
        elif(self.direction=='up'):
            if(self.crossed==0 and self.y<stopLines[self.direction]):
                self.crossed = 1
                vehicles[self.direction]['crossed'] += 1
            if(self.willTurn==1):
                if(self.crossed==0 or self.y>mid[self.direction]['y']):
                    if((self.y>=self.stop or (currentGreen==3 and currentYellow==0) or self.crossed == 1 or self.isEmergency) and (self.index==0 or self.y>(vehicles[self.direction][self.lane][self.index-1].y + vehicles[self.direction][self.lane][self.index-1].currentImage.get_rect().height +  gap2) or vehicles[self.direction][self.lane][self.index-1].turned==1)):
                        self.y -= self.speed
                else:   
                    if(self.turned==0):
                        self.rotateAngle += rotationAngle
                        self.currentImage = pygame.transform.rotate(self.originalImage, -self.rotateAngle)
                        self.x += 1
                        self.y -= 1
                        if(self.rotateAngle==90):
                            self.turned = 1
                    else:
                        if(self.index==0 or self.x<(vehicles[self.direction][self.lane][self.index-1].x - vehicles[self.direction][self.lane][self.index-1].currentImage.get_rect().width - gap2) or self.y>(vehicles[self.direction][self.lane][self.index-1].y + gap2)):
                            self.x += self.speed
            else: 
                if((self.y>=self.stop or self.crossed == 1 or (currentGreen==3 and currentYellow==0) or self.isEmergency) and (self.index==0 or self.y>(vehicles[self.direction][self.lane][self.index-1].y + vehicles[self.direction][self.lane][self.index-1].currentImage.get_rect().height + gap2) or (vehicles[self.direction][self.lane][self.index-1].turned==1))):                
                    self.y -= self.speed

# Initialize traffic signals
def initialize():
    ts1 = TrafficSignal(0, defaultYellow, defaultGreen, defaultMinimum, defaultMaximum)
    signals.append(ts1)
    ts2 = TrafficSignal(ts1.red+ts1.yellow+ts1.green, defaultYellow, defaultGreen, defaultMinimum, defaultMaximum)
    signals.append(ts2)
    ts3 = TrafficSignal(defaultRed, defaultYellow, defaultGreen, defaultMinimum, defaultMaximum)
    signals.append(ts3)
    ts4 = TrafficSignal(defaultRed, defaultYellow, defaultGreen, defaultMinimum, defaultMaximum)
    signals.append(ts4)
    
    global stats_data
    stats_data = {
        'time': [],
        'total_vehicles': [],
        'emergency_vehicles': [],
        'vehicles_passed': {direction: [] for direction in directionNumbers.values()},
        'signal_times': {direction: {'green': [], 'red': [], 'yellow': []} for direction in directionNumbers.values()},
        'fuel_saved': [],
        'co2_reduced': []
    }
    
    repeat()
# Set signal timing based on vehicle detection
def setTime():
    global noOfCars, noOfBikes, noOfBuses, noOfTrucks, noOfRickshaws, noOfLanes
    global carTime, busTime, truckTime, rickshawTime, bikeTime
    os.system("say detecting vehicles, "+directionNumbers[(currentGreen+1)%noOfSignals])

    noOfCars, noOfBuses, noOfTrucks, noOfRickshaws, noOfBikes, noOfAmbulances = 0,0,0,0,0,0
    for j in range(len(vehicles[directionNumbers[nextGreen]][0])):
        vehicle = vehicles[directionNumbers[nextGreen]][0][j]
        if(vehicle.crossed==0):
            vclass = vehicle.vehicleClass
            if vclass == 'bike':
                noOfBikes += 1
            elif vclass == 'ambulance':
                noOfAmbulances += 1
    for i in range(1,3):
        for j in range(len(vehicles[directionNumbers[nextGreen]][i])):
            vehicle = vehicles[directionNumbers[nextGreen]][i][j]
            if(vehicle.crossed==0):
                vclass = vehicle.vehicleClass
                if(vclass=='car'):
                    noOfCars += 1
                elif(vclass=='bus'):
                    noOfBuses += 1
                elif(vclass=='truck'):
                    noOfTrucks += 1
                elif(vclass=='rickshaw'):
                    noOfRickshaws += 1
                elif(vclass=='ambulance'):
                    noOfAmbulances += 1
    
    if noOfAmbulances > 0:
        greenTime = emergencyGreenTime
    else:
        greenTime = math.ceil(((noOfCars*carTime) + (noOfRickshaws*rickshawTime) + (noOfBuses*busTime) + (noOfTrucks*truckTime)+ (noOfBikes*bikeTime))/(noOfLanes+1))
    
    print('Green Time: ',greenTime)
    if(greenTime<defaultMinimum):
        greenTime = defaultMinimum
    elif(greenTime>defaultMaximum):
        greenTime = defaultMaximum
    signals[(currentGreen+1)%(noOfSignals)].green = greenTime
   
# Main signal control loop
def repeat():
    global currentGreen, currentYellow, nextGreen
    while(signals[currentGreen].green>0):
        printStatus()
        updateValues()
        updateStats()
        if(signals[(currentGreen+1)%(noOfSignals)].red==detectionTime):
            thread = threading.Thread(name="detection",target=setTime, args=())
            thread.daemon = True
            thread.start()
            
        checkEmergencyVehicles()
        
        if emergencyOverride:
            handleEmergencySignals()
            
        time.sleep(1)
    currentYellow = 1
    vehicleCountTexts[currentGreen] = "0"
    for i in range(0,3):
        stops[directionNumbers[currentGreen]][i] = defaultStop[directionNumbers[currentGreen]]
        for vehicle in vehicles[directionNumbers[currentGreen]][i]:
            vehicle.stop = defaultStop[directionNumbers[currentGreen]]
    while(signals[currentGreen].yellow>0):
        printStatus()
        updateValues()
        updateStats()
        time.sleep(1)
    currentYellow = 0
    
    signals[currentGreen].green = defaultGreen
    signals[currentGreen].yellow = defaultYellow
    signals[currentGreen].red = defaultRed
       
    currentGreen = nextGreen
    nextGreen = (currentGreen+1)%noOfSignals
    signals[nextGreen].red = signals[currentGreen].yellow+signals[currentGreen].green
    repeat()     

# Print signal status to console
def printStatus():                                                                                           
    for i in range(0, noOfSignals):
        if(i==currentGreen):
            if(currentYellow==0):
                print(" GREEN TS",i+1,"-> r:",signals[i].red," y:",signals[i].yellow," g:",signals[i].green)
            else:
                print("YELLOW TS",i+1,"-> r:",signals[i].red," y:",signals[i].yellow," g:",signals[i].green)
        else:
            print("   RED TS",i+1,"-> r:",signals[i].red," y:",signals[i].yellow," g:",signals[i].green)
    print()

# Update signal timing values
def updateValues():
    for i in range(0, noOfSignals):
        if(i==currentGreen):
            if(currentYellow==0):
                signals[i].green-=1
                signals[i].totalGreenTime+=1
            else:
                signals[i].yellow-=1
        else:
            signals[i].red-=1
            if signals[i].red < 0:
                signals[i].red = 0

# Update statistics for graphs
def updateStats():
    global stats_data, timeElapsed, total_fuel_saved, total_co2_reduction
    
    if timeElapsed % 5 == 0:
        stats_data['time'].append(timeElapsed)
        
        total_vehicles = 0
        for direction in directionNumbers.values():
            vehicles_crossed = vehicles[direction]['crossed']
            stats_data['vehicles_passed'][direction].append(vehicles_crossed)
            total_vehicles += vehicles_crossed
        
        # Calculate fuel saved and CO2 reduction since last update
        new_vehicles = total_vehicles - (stats_data['total_vehicles'][-1] if stats_data['total_vehicles'] else 0)
        new_fuel_saved = new_vehicles * avg_wait_time_reduction * fuel_saved_per_vehicle
        new_co2_reduced = new_fuel_saved * co2_per_liter
        
        total_fuel_saved += new_fuel_saved
        total_co2_reduction += new_co2_reduced
        
        stats_data['total_vehicles'].append(total_vehicles)
        stats_data['emergency_vehicles'].append(emergencyVehicleCount)
        stats_data['fuel_saved'].append(total_fuel_saved)
        stats_data['co2_reduced'].append(total_co2_reduction)
        
        for i, direction in directionNumbers.items():
            stats_data['signal_times'][direction]['green'].append(signals[i].totalGreenTime)
            stats_data['signal_times'][direction]['red'].append(signals[i].red)
            stats_data['signal_times'][direction]['yellow'].append(signals[i].yellow)
# Generate vehicles
def generateVehicles():
    ambulance_timer = 0
    ambulance_interval = 30
    ambulance_probability = 0.8
    
    while(True):
        if timeElapsed > 0 and timeElapsed % ambulance_interval == 0 and ambulance_timer != timeElapsed:
            if random.random() < ambulance_probability:
                ambulance_timer = timeElapsed
                
                red_signal_directions = []
                for i in range(noOfSignals):
                    if i != currentGreen:
                        red_signal_directions.append(i)
                
                if red_signal_directions:
                    direction_number = random.choice(red_signal_directions)
                    lane_number = random.randint(1, 2)
                    will_turn = 0
                    
                    Vehicle(lane_number, 'ambulance', direction_number, directionNumbers[direction_number], will_turn)
                    print(f"Emergency vehicle generated at time {timeElapsed} in direction {directionNumbers[direction_number]} (RED SIGNAL)")
                    
                    time.sleep(0.75)
                    continue
            
        vehicle_type = random.randint(0, 4)
        if(vehicle_type == 4):
            lane_number = 0
        else:
            lane_number = random.randint(0, 1) + 1
            
        will_turn = 0
        if(lane_number == 2):
            temp = random.randint(0, 4)
            if(temp <= 2):
                will_turn = 1
            elif(temp > 2):
                will_turn = 0
                
        temp = random.randint(0, 999)
        direction_number = 0
        a = [400, 800, 900, 1000]
        if(temp < a[0]):
            direction_number = 0
        elif(temp < a[1]):
            direction_number = 1
        elif(temp < a[2]):
            direction_number = 2
        elif(temp < a[3]):
            direction_number = 3
            
        Vehicle(lane_number, vehicleTypes[vehicle_type], direction_number, directionNumbers[direction_number], will_turn)
        time.sleep(0.75)

## Simulation time tracking
def simulationTime():
    global timeElapsed, simTime
    while(True):
        timeElapsed += 1
        time.sleep(1)
        if(timeElapsed==simTime):
            totalVehicles = 0
            print('Lane-wise Vehicle Counts')
            for i in range(noOfSignals):
                print('Lane',i+1,':',vehicles[directionNumbers[i]]['crossed'])
                totalVehicles += vehicles[directionNumbers[i]]['crossed']
            print('Total vehicles passed: ',totalVehicles)
            print('Total time passed: ',timeElapsed)
            print('No. of vehicles passed per unit time: ',(float(totalVehicles)/float(timeElapsed)))
            os._exit(1)

# Create traffic flow graph
def create_traffic_flow_graph():
    if len(stats_data['time']) < 2:
        return None
    
    plt.figure(figsize=(5, 3), facecolor='#f0f0f0')
    for direction in directionNumbers.values():
        plt.plot(stats_data['time'], stats_data['vehicles_passed'][direction], label=direction.capitalize(), linewidth=2)
    
    plt.title('Traffic Flow by Direction', fontweight='bold')
    plt.xlabel('Time (s)')
    plt.ylabel('Vehicles Passed')
    plt.legend(loc='upper left', fontsize='small')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    canvas = agg.FigureCanvasAgg(plt.gcf())
    canvas.draw()
    renderer = canvas.get_renderer()
    raw_data = renderer.tostring_rgb()
    size = canvas.get_width_height()
    
    surf = pygame.image.fromstring(raw_data, size, "RGB")
    plt.close()
    
    return surf
# Create total vehicles graph
def create_total_vehicles_graph():
    if len(stats_data['time']) < 2:
        return None
    
    plt.figure(figsize=(5, 3))
    plt.plot(stats_data['time'], stats_data['total_vehicles'], 'g-', linewidth=2)
    
    plt.title('Total Vehicles Passed')
    plt.xlabel('Time (s)')
    plt.ylabel('Count')
    plt.grid(True, alpha=0.3)
    
    canvas = agg.FigureCanvasAgg(plt.gcf())
    canvas.draw()
    renderer = canvas.get_renderer()
    raw_data = renderer.tostring_rgb()
    size = canvas.get_width_height()
    
    surf = pygame.image.fromstring(raw_data, size, "RGB")
    plt.close()
    
    return surf

# Create fuel emission graph
def create_fuel_emission_graph():
    if len(stats_data['time']) < 2:
        return None
    
    plt.figure(figsize=(5, 3))
    
    # Plot fuel saved
    plt.plot(stats_data['time'], stats_data['fuel_saved'], 'g-', linewidth=2, label='Fuel Saved (L)')
    
    # Plot CO2 reduction on secondary y-axis
    ax2 = plt.gca().twinx()
    ax2.plot(stats_data['time'], stats_data['co2_reduced'], 'r--', linewidth=2, label='CO₂ Reduced (kg)')
    ax2.set_ylabel('CO₂ Reduced (kg)', color='r')
    
    plt.title('Environmental Impact')
    plt.xlabel('Time (s)')
    plt.ylabel('Fuel Saved (L)', color='g')
    plt.grid(True, alpha=0.3)
    plt.legend(loc='upper left')
    ax2.legend(loc='upper right')
    
    canvas = agg.FigureCanvasAgg(plt.gcf())
    canvas.draw()
    renderer = canvas.get_renderer()
    raw_data = renderer.tostring_rgb()
    size = canvas.get_width_height()
    
    surf = pygame.image.fromstring(raw_data, size, "RGB")
    plt.close()
    
    return surf

# Main function
def Main():
    global timeElapsed, emergencyPassageAlert, emergencyPassageTime, emergencyAlertDuration
    global emergencyVehiclePresent, emergencyDirection, emergencyTimer, emergencyOverride, emergencyPriorityActive
    global emergencyVehicleCount, emergencyCooldown, ambulance_siren
# Create emergency response graph
def create_emergency_response_graph():
    if len(stats_data['time']) < 2:
        return None
    
    plt.figure(figsize=(5, 3))
    plt.plot(stats_data['time'], stats_data['emergency_vehicles'], 'r-', linewidth=3)
    
    plt.title('Emergency Vehicles Passed')
    plt.xlabel('Time (s)')
    plt.ylabel('Count')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    canvas = agg.FigureCanvasAgg(plt.gcf())
    canvas.draw()
    renderer = canvas.get_renderer()
    raw_data = renderer.tostring_rgb()
    size = canvas.get_width_height()
    
    surf = pygame.image.fromstring(raw_data, size, "RGB")
    plt.close()
    
    return surf

# Create signal timing graph
def create_signal_timing_graph():
    if len(stats_data['time']) < 2:
        return None
    
    plt.figure(figsize=(5, 3))
    
    for i, direction in directionNumbers.items():
        plt.plot(stats_data['time'], stats_data['signal_times'][direction]['green'], 
                 label=f"{direction.capitalize()} Green")
    
    plt.title('Signal Green Time by Direction')
    plt.xlabel('Time (s)')
    plt.ylabel('Cumulative Green Time (s)')
    plt.legend(loc='upper left', fontsize='x-small')
    plt.grid(True, alpha=0.3)
    
    canvas = agg.FigureCanvasAgg(plt.gcf())
    canvas.draw()
    renderer = canvas.get_renderer()
    raw_data = renderer.tostring_rgb()
    size = canvas.get_width_height()
    
    surf = pygame.image.fromstring(raw_data, size, "RGB")
    plt.close()
    
    return surf

# Create total vehicles graph
def create_total_vehicles_graph():
    if len(stats_data['time']) < 2:
        return None
    
    plt.figure(figsize=(5, 3))
    plt.plot(stats_data['time'], stats_data['total_vehicles'], 'g-', linewidth=2)
    
    plt.title('Total Vehicles Passed')
    plt.xlabel('Time (s)')
    plt.ylabel('Count')
    plt.grid(True, alpha=0.3)
    
    canvas = agg.FigureCanvasAgg(plt.gcf())
    canvas.draw()
    renderer = canvas.get_renderer()
    raw_data = renderer.tostring_rgb()
    size = canvas.get_width_height()
    
    surf = pygame.image.fromstring(raw_data, size, "RGB")
    plt.close()
    
    return surf

# Create fuel emission graph
def create_fuel_emission_graph():
    if len(stats_data['time']) < 2:
        return None
    
    plt.figure(figsize=(5, 3))
    
    # Plot fuel saved
    plt.plot(stats_data['time'], stats_data['fuel_saved'], 'g-', linewidth=2, label='Fuel Saved (L)')
    
    # Plot CO2 reduction on secondary y-axis
    ax2 = plt.gca().twinx()
    ax2.plot(stats_data['time'], stats_data['co2_reduced'], 'r--', linewidth=2, label='CO₂ Reduced (kg)')
    ax2.set_ylabel('CO₂ Reduced (kg)', color='r')
    
    plt.title('Environmental Impact')
    plt.xlabel('Time (s)')
    plt.ylabel('Fuel Saved (L)', color='g')
    plt.grid(True, alpha=0.3)
    plt.legend(loc='upper left')
    ax2.legend(loc='upper right')
    
    canvas = agg.FigureCanvasAgg(plt.gcf())
    canvas.draw()
    renderer = canvas.get_renderer()
    raw_data = renderer.tostring_rgb()
    size = canvas.get_width_height()
    
    surf = pygame.image.fromstring(raw_data, size, "RGB")
    plt.close()
    
    return surf

# Main function
def Main():
    global timeElapsed, emergencyPassageAlert, emergencyPassageTime, emergencyAlertDuration
    global emergencyVehiclePresent, emergencyDirection, emergencyTimer, emergencyOverride, emergencyPriorityActive
    global emergencyVehicleCount, emergencyCooldown, ambulance_siren
    # Load ambulance siren sound
    try:
        base_path = os.path.dirname(os.path.abspath(__file__))
        siren_path = os.path.join(base_path, 'sounds', 'ambulance_siren.wav')
        if os.path.exists(siren_path):
            ambulance_siren = pygame.mixer.Sound(siren_path)
            ambulance_siren.set_volume(0.7)  # Set volume to 70%
        else:
            print(f"Warning: Could not find ambulance siren sound at {siren_path}")
            # Create directory for sounds if it doesn't exist
            sounds_dir = os.path.join(base_path, 'sounds')
            if not os.path.exists(sounds_dir):
                os.makedirs(sounds_dir)
                print(f"Created sounds directory at {sounds_dir}")
                print("Please add ambulance_siren.wav to this directory")
    except Exception as e:
        print(f"Error loading ambulance siren: {e}")
        ambulance_siren = None
    
    thread1 = threading.Thread(name="initialization",target=initialize, args=())
    thread1.daemon = True
    thread1.start()

    # Define colors
    black = (0, 0, 0)
    white = (255, 255, 255)
    red = (255, 0, 0)
    yellow = (255, 232, 0)
    green = (0, 200, 0)
    blue = (0, 0, 200)
    light_blue = (100, 150, 255)
    gray = (100, 100, 100)
    light_gray = (220, 220, 220)
    
    # Set up screen
    screenWidth = 1400
    screenHeight = 800
    screenSize = (screenWidth, screenHeight)
    
    # Define base path and image paths
    base_path = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(base_path, 'images')
    
    # Use the specified intersection image
    try:
        background = pygame.image.load('C:\\Users\\raksh\\OneDrive\\Desktop\\major project\\Adaptive-Traffic-Signal-Timer-main\\Adaptive-Traffic-Signal-Timer-main\\Code\\YOLO\\darkflow\\images\\mod_int.png')
    except pygame.error:
        print("Error: Could not load mod_int.png")
        print("Please ensure the file exists in the specified directory")
        sys.exit(1)
        
    screen = pygame.display.set_mode(screenSize)
    pygame.display.set_caption("Smart Traffic Signal Simulation And Optimization System")
    
    # Set up custom font
    try:
        font_path = os.path.join(base_path, 'fonts', 'arial.ttf')
        if os.path.exists(font_path):
            font = pygame.font.Font(font_path, 24)
            small_font = pygame.font.Font(font_path, 18)
            title_font = pygame.font.Font(font_path, 30)
        else:
            font = pygame.font.SysFont('Arial', 24)
            small_font = pygame.font.SysFont('Arial', 18)
            title_font = pygame.font.SysFont('Arial', 30)
    except:
        font = pygame.font.SysFont('Arial', 24)
        small_font = pygame.font.SysFont('Arial', 18)
        title_font = pygame.font.SysFont('Arial', 30)

    # Use the defined image_path for signal images
    try:
        signals_path = os.path.join(image_path, 'signals')
        redSignal = pygame.image.load(os.path.join(signals_path, 'red.png'))
        yellowSignal = pygame.image.load(os.path.join(signals_path, 'yellow.png'))
        greenSignal = pygame.image.load(os.path.join(signals_path, 'green.png'))
    except pygame.error as e:
        print(f"Error loading signal images: {e}")
        print("Please ensure signal images exist in the images/signals directory")
        sys.exit(1)
        
    thread2 = threading.Thread(name="generateVehicles",target=generateVehicles, args=())
    thread2.daemon = True
    thread2.start()
    
    thread3 = threading.Thread(name="simTime",target=simulationTime, args=())
    thread3.daemon = True
    thread3.start()
    
    # Dashboard controls
    dashboard_active = False
    dashboard_button = pygame.Rect(1200, 700, 180, 40)
    
    # Add save results button - MODIFIED: Moved to center position
    save_results_button = pygame.Rect(1000, 700, 180, 40)
    
    # REMOVED: Export PDF button
    # export_pdf_button = pygame.Rect(800, 700, 180, 40)
    
    save_message = ""
    save_message_time = 0
    
    # Initialize graph surfaces
    traffic_flow_graph = None
    emergency_graph = None
    signal_timing_graph = None
    total_vehicles_graph = None
    
    graph_update_timer = 0
    graph_update_interval = 5
    
    # Main game loop
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if dashboard_button.collidepoint(event.pos):
                    dashboard_active = not dashboard_active
                elif save_results_button.collidepoint(event.pos):
                    # MODIFIED: Save results and automatically generate PDF
                    save_message = save_simulation_results()
                    save_message_time = timeElapsed
                    
                    # Get the latest report file and generate PDF
                    reports_dir = os.path.join(base_path, 'reports')
                    if os.path.exists(reports_dir):
                        report_files = [f for f in os.listdir(reports_dir) if f.startswith('traffic_report_') and f.endswith('.txt')]
                        if report_files:
                            latest_report = sorted(report_files)[-1]
                            report_path = os.path.join(reports_dir, latest_report)
                            # Automatically export to PDF
                            export_report_to_pdf(report_path)
                        else:
                            save_message = "No reports found. Save results first."
                            save_message_time = timeElapsed
                    else:
                        save_message = "Reports directory not found"
                        save_message_time = timeElapsed
                
                # REMOVED: Export PDF button handling
        
        # Draw background
        screen.blit(background, (0, 0))
        
        # Draw title bar
        pygame.draw.rect(screen, (50, 50, 80), (0, 0, screenWidth, 60))
        title_text = title_font.render("Smart Traffic Signal Simulation And Optimization System", True, white)
        screen.blit(title_text, (screenWidth//2 - title_text.get_width()//2, 15))
        
        # Draw traffic signals
        for i in range(0, noOfSignals):
            if(i==currentGreen):
                if(currentYellow==1):
                    signals[i].signalText = signals[i].yellow
                    screen.blit(yellowSignal, signalCoods[i])
                else:
                    signals[i].signalText = signals[i].green
                    screen.blit(greenSignal, signalCoods[i])
            else:
                if(signals[i].red<=10):
                    signals[i].signalText = signals[i].red
                else:
                    signals[i].signalText = "---"
                screen.blit(redSignal, signalCoods[i])
        
        # Draw signal timers
        signalTexts = ["", "", "", ""]
        
        for i in range(0,noOfSignals):  
            signalTexts[i] = font.render(str(signals[i].signalText), True, white, black)
            screen.blit(signalTexts[i],signalTimerCoods[i]) 
            displayText = vehicles[directionNumbers[i]]['crossed']
            vehicleCountTexts[i] = font.render(str(displayText), True, black, white)
            screen.blit(vehicleCountTexts[i],vehicleCountCoods[i])

        # Draw time elapsed
        pygame.draw.rect(screen, light_blue, (1050, 70, 330, 150), 0, 10)
        pygame.draw.rect(screen, blue, (1050, 70, 330, 150), 3, 10)
        
        timeElapsedText = font.render(("Time Elapsed: "+str(timeElapsed)+"s"), True, black)
        screen.blit(timeElapsedText,(1070, 80))
        
        # Draw emergency vehicle alerts
        if emergencyPassageAlert:
            if timeElapsed - emergencyPassageTime < emergencyAlertDuration:
                pygame.draw.rect(screen, red, (20, 70, 310, 50), 0, 10)
                alertText = font.render("EMERGENCY VEHICLE PASSED!", True, white)
                text_width = alertText.get_width()
                screen.blit(alertText, (20 + (310 - text_width) // 2, 85))
                
                if timeElapsed % 2 == 0:
                    pygame.draw.rect(screen, white, (20, 70, 310, 50), 3, 10)
            else:
                emergencyPassageAlert = False
        
        # Draw emergency vehicle status
        if emergencyVehiclePresent:
            pygame.draw.rect(screen, red, (350, 70, 350, 150), 0, 10)
            pygame.draw.rect(screen, (200, 0, 0), (350, 70, 350, 150), 3, 10)
            
            emergencyText = font.render("EMERGENCY VEHICLE DETECTED", True, white)
            screen.blit(emergencyText, (360, 80))
            
            dirText = font.render("Priority: " + directionNumbers[emergencyDirection].upper() + " LANE", True, white)
            screen.blit(dirText, (360, 110))
            
            if emergencyPriorityActive:
                timerText = font.render(f"Priority Time: {emergencyTimer}s", True, white)
                screen.blit(timerText, (360, 140))
                
                statusText = font.render("ALL OTHER LANES STOPPED", True, white)
                screen.blit(statusText, (360, 170))
                
                if timeElapsed % 2 == 0:
                    pygame.draw.rect(screen, (255, 150, 150), (355, 165, 340, 30), 2, 5)
            
            if emergencyOverride and timeElapsed % 2 == 0:
                pygame.draw.circle(screen, (255, 255, 0), (330, 85), 10)
        
        # Draw statistics
        statsText = font.render(f"Ambulances Passed: {emergencyVehicleCount}", True, black)
        screen.blit(statsText, (1070, 110))
        
        if emergencyCooldown > 0:
            cooldownText = font.render(f"Signal Reset: {emergencyCooldown}s", True, black)
            screen.blit(cooldownText, (1070, 140))
        
       # Draw dashboard button with improved styling
        pygame.draw.rect(screen, blue, dashboard_button, 0, 10)
        pygame.draw.rect(screen, (0, 0, 150), dashboard_button, 2, 10)
        dashboard_text = font.render("Toggle Dashboard", True, white)
        screen.blit(dashboard_text, (dashboard_button.x + 10, dashboard_button.y + 8))
        
        # MODIFIED: Draw save results button with new text
        pygame.draw.rect(screen, (50, 150, 50), save_results_button, 0, 10)
        pygame.draw.rect(screen, (0, 100, 0), save_results_button, 2, 10)
        save_text = font.render("Save Results", True, white)
        screen.blit(save_text, (save_results_button.x + 30, save_results_button.y + 8))
        
        # REMOVED: Export PDF button drawing code
        
        # Display save message if applicable
        if save_message and timeElapsed - save_message_time < 5:
            message_surface = pygame.Surface((400, 40))
            message_surface.set_alpha(220)
            message_surface.fill((240, 240, 250))
            screen.blit(message_surface, (800, 650))
            pygame.draw.rect(screen, (50, 150, 50), (800, 650, 400, 40), 2, 10)
            message_text = font.render(save_message, True, (50, 150, 50))
            screen.blit(message_text, (810, 658))
        
        # Draw dashboard if active
        if dashboard_active:
            # Create a semi-transparent overlay for the dashboard
            dashboard_surface = pygame.Surface((550, 680))
            dashboard_surface.set_alpha(240)
            dashboard_surface.fill((240, 240, 250))
            screen.blit(dashboard_surface, (20, 100))
         # Position graphs with better spacing
            if traffic_flow_graph:
                screen.blit(traffic_flow_graph, (45, 150))
                
            if emergency_graph:
                screen.blit(emergency_graph, (45, 300))
                
            if signal_timing_graph:
                screen.blit(signal_timing_graph, (45, 450))
                
            if total_vehicles_graph:
                screen.blit(total_vehicles_graph, (45, 600))
            
            # Draw fuel emission graph
            fuel_emission_graph = create_fuel_emission_graph()
            if fuel_emission_graph:
                screen.blit(fuel_emission_graph, (45, 750))
                graph_title = font.render("Environmental Impact", True, black)
                screen.blit(graph_title, (45, 730))
            
            # Display current fuel and CO2 stats
            fuel_text = font.render(f"Fuel Saved: {total_fuel_saved:.2f} liters", True, (0, 100, 0))
            co2_text = font.render(f"CO₂ Reduced: {total_co2_reduction:.2f} kg", True, (150, 0, 0))
            screen.blit(fuel_text, (350, 730))
            screen.blit(co2_text, (350, 760))
            # Add a border to the dashboard
            pygame.draw.rect(screen, (100, 100, 200), (20, 100, 550, 680), 3, 10)
            
            # Dashboard title with better styling
            title_text = font.render("Real-time Traffic Statistics", True, (50, 50, 100))
            title_rect = title_text.get_rect(center=(20 + 550//2, 120))
            screen.blit(title_text, title_rect)
            
            # Horizontal separator line
            pygame.draw.line(screen, (100, 100, 200), (40, 140), (550, 140), 2)
            
            # Update graphs periodically
            if timeElapsed - graph_update_timer >= graph_update_interval:
                traffic_flow_graph = create_traffic_flow_graph()
                emergency_graph = create_emergency_response_graph()
                signal_timing_graph = create_signal_timing_graph()
                total_vehicles_graph = create_total_vehicles_graph()
                graph_update_timer = timeElapsed
            
            # Position graphs with better spacing
            if traffic_flow_graph:
                screen.blit(traffic_flow_graph, (45, 150))
                
            if emergency_graph:
                screen.blit(emergency_graph, (45, 300))
                
            if signal_timing_graph:
                screen.blit(signal_timing_graph, (45, 450))
                
            if total_vehicles_graph:
                screen.blit(total_vehicles_graph, (45, 600))
            
            # Enhanced statistics panel on the right side
            stats_panel = pygame.Surface((300, 200))
            stats_panel.set_alpha(220)
            stats_panel.fill((230, 230, 250))
            screen.blit(stats_panel, (600, 550))
            pygame.draw.rect(screen, (100, 100, 200), (600, 550, 300, 200), 2, 10)
            
            # Stats title
            stats_title = font.render("Summary Statistics", True, (50, 50, 100))
            stats_title_rect = stats_title.get_rect(center=(600 + 300//2, 570))
            screen.blit(stats_title, stats_title_rect)
            
            # Enhanced stats display with icons or colored indicators
            stats_text = [
                f"Total Vehicles: {sum(vehicles[d]['crossed'] for d in directionNumbers.values())}",
                f"Emergency Vehicles: {emergencyVehicleCount}",
                f"Avg. Green Time: {sum(s.totalGreenTime for s in signals)/max(1, len(signals)):.1f}s",
                f"Simulation Time: {timeElapsed}s",
                f"Vehicles/Second: {sum(vehicles[d]['crossed'] for d in directionNumbers.values())/max(1, timeElapsed):.2f}"
            ]
            
            for i, text in enumerate(stats_text):
                # Draw colored circle indicators
                indicator_color = (0, 150, 0) if i != 1 else (200, 0, 0)
                pygame.draw.circle(screen, indicator_color, (615, 600 + i*30), 5)
                
                # Draw the text
                stat_text = font.render(text, True, (20, 20, 50))
                screen.blit(stat_text, (630, 590 + i*30))

        # Draw vehicles with special highlighting for emergency vehicles
        for vehicle in simulation:  
            if vehicle.isEmergency and timeElapsed % 2 == 0:
                # Add flashing effect for emergency vehicles
                pygame.draw.rect(screen, red, 
                                (vehicle.x-5, vehicle.y-5, 
                                 vehicle.currentImage.get_rect().width+10, 
                                 vehicle.currentImage.get_rect().height+10), 2, 5)
                
                # Add light effect
                if timeElapsed % 4 < 2:
                    pygame.draw.circle(screen, (255, 0, 0), 
                                      (int(vehicle.x + vehicle.currentImage.get_rect().width//2), 
                                       int(vehicle.y + vehicle.currentImage.get_rect().height//2)), 
                                      20, 2)
                else:
                    pygame.draw.circle(screen, (0, 0, 255), 
                                      (int(vehicle.x + vehicle.currentImage.get_rect().width//2), 
                                       int(vehicle.y + vehicle.currentImage.get_rect().height//2)), 
                                      20, 2)
                
            screen.blit(vehicle.currentImage, [vehicle.x, vehicle.y])
            vehicle.move()
            
        pygame.display.update()
# Create total vehicles graph
def create_total_vehicles_graph():
    if len(stats_data['time']) < 2:
        return None
    
    plt.figure(figsize=(5, 3))
    plt.plot(stats_data['time'], stats_data['total_vehicles'], 'g-', linewidth=2)
    
    plt.title('Total Vehicles Passed')
    plt.xlabel('Time (s)')
    plt.ylabel('Count')
    plt.grid(True, alpha=0.3)
    
    canvas = agg.FigureCanvasAgg(plt.gcf())
    canvas.draw()
    renderer = canvas.get_renderer()
    raw_data = renderer.tostring_rgb()
    size = canvas.get_width_height()
    
    surf = pygame.image.fromstring(raw_data, size, "RGB")
    plt.close()
    
    return surf
# Function to export report to PDF
def export_report_to_pdf(report_file):
    try:
        # Import necessary modules
        import os
        import sys
        import platform
        import subprocess
        import matplotlib.pyplot as plt
        import numpy as np
        import io
        
        # Check if fpdf is installed
        try:
            import fpdf
        except ImportError:
            print("Installing fpdf package...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "fpdf"])
            import fpdf
        
        # Read the text report
        with open(report_file, 'r') as f:
            report_text = f.read()
        
        # Create PDF file path
        pdf_file = report_file.replace('.txt', '.pdf')
        
        # Create custom PDF class with header and footer
        class PDF(fpdf.FPDF):
            def header(self):
                # Updated header with a more attractive gradient color scheme
                self.set_fill_color(76, 40, 130)  # Deep purple
                self.rect(0, 0, 210, 25, 'F')
                self.set_fill_color(106, 90, 205)  # Slate blue
                self.rect(0, 15, 210, 10, 'F')
                
                # Add title with improved styling
                self.set_font('Arial', 'B', 22)
                self.set_text_color(255, 255, 255)
                self.cell(0, 15, 'Smart Traffic Signal Simulation', 0, 1, 'C')
                
                # Add subtitle
                self.set_font('Arial', 'I', 12)
                self.set_text_color(240, 240, 240)
                self.cell(0, 5, 'Analysis & Optimization Report', 0, 1, 'C')
                
                # Add date on the right
                self.set_font('Arial', 'I', 9)
                self.set_text_color(220, 220, 220)
                self.cell(0, 5, f"Generated: {report_file.split('_')[-1].replace('.txt', '')}", 0, 1, 'R')
                
                # Line break
                self.ln(10)
            
            def footer(self):
                # Position at 1.5 cm from bottom
                self.set_y(-15)
                # Set font
                self.set_font('Arial', 'I', 8)
                self.set_text_color(128, 128, 128)
                # Page number
                self.cell(0, 10, 'Page ' + str(self.page_no()) + '/{nb}', 0, 0, 'C')
                # Add a decorative line
                self.line(10, self.get_y()-5, 200, self.get_y()-5)
            
            # Add custom rounded rectangle method
            def rounded_rect(self, x, y, w, h, r, style=''):
                # Style can be 'F' for fill, 'D' for draw, or 'DF' for both
                k = self.k
                hp = self.h
                if style == '':
                    style = 'D'
                if style == 'F':
                    op = 'f'
                elif style == 'FD' or style == 'DF':
                    op = 'B'
                else:
                    op = 'S'
                
                # Scale by k (internal PDF unit conversion)
                x *= k
                y = (hp - y) * k
                w *= k
                h *= k
                r *= k
                
                # Draw the rounded rectangle using bezier curves
                self._out('q')  # Save state
                self._out('%.2f %.2f m' % (x + r, y))  # Move to first point
                self._out('%.2f %.2f l' % (x + w - r, y))  # Line to second point
                
                # Top right corner
                self._out('%.2f %.2f %.2f %.2f %.2f %.2f c' % 
                         (x + w - r/2, y, x + w, y - r/2, x + w, y - r))
                self._out('%.2f %.2f l' % (x + w, y - h + r))
                
                # Bottom right corner
                self._out('%.2f %.2f %.2f %.2f %.2f %.2f c' % 
                         (x + w, y - h + r/2, x + w - r/2, y - h, x + w - r, y - h))
                self._out('%.2f %.2f l' % (x + r, y - h))
                
                # Bottom left corner
                self._out('%.2f %.2f %.2f %.2f %.2f %.2f c' % 
                         (x + r/2, y - h, x, y - h + r/2, x, y - h + r))
                self._out('%.2f %.2f l' % (x, y - r))
                
                # Top left corner
                self._out('%.2f %.2f %.2f %.2f %.2f %.2f c' % 
                         (x, y - r/2, x + r/2, y, x + r, y))
                
                self._out(op)
                self._out('Q')  # Restore state
        
        # Create PDF document
        pdf = PDF(orientation='P', unit='mm', format='A4')
        pdf.alias_nb_pages()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        
        # Set fonts - using built-in fonts to avoid font issues
        pdf.set_font('Arial', '', 10)
        pdf.set_text_color(0, 0, 0)
        
        # Add a decorative element at the top of the first page
        pdf.set_draw_color(76, 40, 130)  # Deep purple
        pdf.set_line_width(0.5)
        pdf.line(10, 40, 200, 40)
        
        # Parse the text report into sections
        sections = report_text.split('\n\n')
        
        # Process each section
        for section in sections:
            if "=================================================================" in section:
                continue
            
            if "TRAFFIC FLOW STATISTICS" in section or "DIRECTION STATISTICS" in section or \
               "EMERGENCY VEHICLE STATISTICS" in section or "ENVIRONMENTAL IMPACT" in section or \
               "SIGNAL EFFICIENCY" in section:
                # This is a section header - CHANGED: Updated styling
                pdf.ln(5)
                pdf.set_fill_color(106, 90, 205)  # Slate blue
                pdf.set_text_color(255, 255, 255)
                pdf.set_font('Arial', 'B', 12)
                section_lines = section.split('\n')
                
                # Add rounded rectangle for section headers
                pdf.rounded_rect(10, pdf.get_y(), 190, 8, 2, 'F')
                pdf.cell(0, 8, section_lines[0], 0, 1, 'L')
                pdf.set_text_color(0, 0, 0)
                pdf.set_font('Arial', '', 10)
                
                # Add the rest of the section as normal text with improved formatting
                for line in section_lines[1:]:
                    if line.strip() and not line.startswith('-'):
                        if ":" in line:  # Format key-value pairs differently
                            key, value = line.split(":", 1)
                            pdf.set_font('Arial', 'B', 10)
                            pdf.cell(60, 6, key.strip() + ":", 0, 0, 'L')
                            pdf.set_font('Arial', '', 10)
                            pdf.cell(0, 6, value.strip(), 0, 1, 'L')
                        else:
                            pdf.cell(0, 6, line.strip(), 0, 1, 'L')
            else:
                # Regular content
                for line in section.split('\n'):
                    if line.strip():
                        pdf.cell(0, 6, line.strip(), 0, 1, 'L')
        
        # Add graphs if they exist
        base_path = os.path.dirname(os.path.abspath(report_file))
        timestamp = os.path.basename(report_file).replace('traffic_report_', '').replace('.txt', '')
        
        results_dir = os.path.join(os.path.dirname(base_path), 'results')
        graph_files = [
            os.path.join(results_dir, 'traffic_flow_{0}.png'.format(timestamp)),
            os.path.join(results_dir, 'emergency_vehicles_{0}.png'.format(timestamp)),
            os.path.join(results_dir, 'signal_timing_{0}.png'.format(timestamp)),
            os.path.join(results_dir, 'total_vehicles_{0}.png'.format(timestamp)),
            os.path.join(results_dir, 'fuel_emission_{0}.png'.format(timestamp))
        ]
        
        # Filter only existing graph files
        existing_graphs = [g for g in graph_files if os.path.exists(g)]
        
        # CHANGED: Improved graph presentation
        if existing_graphs:
            pdf.add_page()
            
            # Add attractive header for graphs section
            pdf.set_fill_color(76, 40, 130)  # Deep purple
            pdf.rounded_rect(10, pdf.get_y(), 190, 10, 3, 'F')
            pdf.set_text_color(255, 255, 255)
            pdf.set_font('Arial', 'B', 14)
            pdf.cell(0, 10, 'Simulation Graphs & Analytics', 0, 1, 'C')
            pdf.ln(5)
            pdf.set_text_color(0, 0, 0)
            
            # Add a brief explanation
            pdf.set_font('Arial', 'I', 9)
            pdf.set_fill_color(240, 240, 250)
            pdf.rounded_rect(10, pdf.get_y(), 190, 8, 2, 'F')
            pdf.cell(0, 8, 'The following graphs visualize key metrics from the traffic simulation', 0, 1, 'C')
            pdf.ln(5)
            
            # Group graphs 3 per page with better spacing and layout
            graphs_per_page = 3
            
            for i in range(0, len(existing_graphs), graphs_per_page):
                if i > 0:
                    pdf.add_page()
                
                group = existing_graphs[i:i+graphs_per_page]
                height_per_graph = 75  # mm
                
                for j, graph_file in enumerate(group):
                    try:
                        # Add graph title with improved styling
                        graph_name = os.path.basename(graph_file).split('_')[0].replace('_', ' ').title()
                        pdf.set_font('Arial', 'B', 12)
                        pdf.set_fill_color(230, 230, 250)  # Light purple background
                        pdf.rounded_rect(20, pdf.get_y(), 170, 8, 2, 'F')
                        pdf.cell(0, 8, graph_name + " Analysis", 0, 1, 'C')
                        
                        # Calculate position for centered image
                        img_width = 160  # mm
                        img_height = height_per_graph - 15  # mm
                        x_pos = (210 - img_width) / 2
                        
                        # Add a light background for the graph
                        pdf.set_fill_color(248, 248, 255)  # Ghost white
                        pdf.rounded_rect(x_pos-5, pdf.get_y(), img_width+10, img_height+5, 3, 'F')
                        
                        # Add the graph image
                        pdf.image(graph_file, x=x_pos, y=pdf.get_y()+2, w=img_width, h=img_height)
                        
                        # Add a separator line
                        pdf.ln(img_height + 10)
                        if j < len(group) - 1:  # Don't add line after the last graph
                            pdf.set_draw_color(200, 200, 220)
                            pdf.line(40, pdf.get_y()-5, 170, pdf.get_y()-5)
                    except Exception as e:
                        pdf.cell(0, 10, "Error loading graph: {0}".format(str(e)), 0, 1, 'L')
        
                      # Add a pie chart showing vehicle distribution by direction
        try:
            # Extract vehicle counts by direction from the report
            direction_counts = {}
            for section in sections:
                if "DIRECTION STATISTICS" in section:
                    lines = section.split('\n')
                    current_direction = None
                    for line in lines:
                        if "Direction:" in line:
                            current_direction = line.split(':')[1].strip()
                        elif current_direction and "Vehicles Passed:" in line:
                            count = int(line.split(':')[1].strip())
                            direction_counts[current_direction] = count
            
            if direction_counts:
                                # Add a traffic distribution summary page
                pdf.add_page()
                pdf.set_fill_color(76, 40, 130)  # Deep purple
                pdf.rounded_rect(10, pdf.get_y(), 190, 10, 3, 'F')
                pdf.set_text_color(255, 255, 255)
                pdf.set_font('Arial', 'B', 14)
                pdf.cell(0, 10, 'Traffic Distribution Summary', 0, 1, 'C')
                pdf.ln(5)
                pdf.set_text_color(0, 0, 0)
                # Extract direction statistics from the report
                direction_stats = {}
                for section in sections:
                    if "DIRECTION STATISTICS" in section:
                        lines = section.split('\n')
                        current_direction = None
                        for line in lines:
                            if "Direction:" in line:
                                current_direction = line.split(':')[1].strip()
                            elif current_direction and "Vehicles Passed:" in line:
                                count = int(line.split(':')[1].strip())
                                direction_stats[current_direction] = count
                            elif current_direction and "Percentage of Total:" in line:
                                percentage = float(line.split(':')[1].strip().replace('%', ''))
                                if current_direction in direction_stats:
                                    direction_stats[current_direction] = (direction_stats[current_direction], percentage)

                # Create a bar chart for direction comparison
                if direction_stats:
                    
                    # Create bar chart with improved styling
                    plt.figure(figsize=(8, 5), facecolor='#f8f8ff')
                    
                    # Extract data for plotting
                    directions = list(direction_stats.keys())
                    counts = [data[0] if isinstance(data, tuple) else data for data in direction_stats.values()]
                    
                    # Create bars with gradient colors
                    bars = plt.bar(directions, counts, color=['#8a2be2', '#4169e1', '#20b2aa', '#ff6347'])
                    
                    # Add data labels on top of bars
                    for bar in bars:
                        height = bar.get_height()
                        plt.text(bar.get_x() + bar.get_width()/2., height + 5,
                                f'{height}', ha='center', va='bottom', fontweight='bold')
                    
                    plt.title('Traffic Volume by Direction', fontsize=16, fontweight='bold', pad=20, color='#483d8b')
                    plt.xlabel('Direction', fontsize=12, fontweight='bold', labelpad=10)
                    plt.ylabel('Number of Vehicles', fontsize=12, fontweight='bold', labelpad=10)
                    plt.grid(axis='y', alpha=0.3)
                    plt.tight_layout()
                    
                    # Save the bar chart to a BytesIO object
                    bar_buf = io.BytesIO()
                    plt.savefig(bar_buf, format='png', dpi=120, bbox_inches='tight')
                    bar_buf.seek(0)
                    plt.close()
                    
                    # Add the bar chart to the PDF
                    pdf.image(bar_buf, x=20, y=None, w=170)
                    pdf.ln(5)
                    
                    # Create pie chart for percentage distribution
                    plt.figure(figsize=(8, 6), facecolor='#f8f8ff')
                    
                    # Extract percentages for pie chart
                    percentages = [data[1] if isinstance(data, tuple) else (data/sum(counts)*100) 
                                  for data in direction_stats.values()]
                    
                    # Use a more attractive color scheme
                    colors = ['#8a2be2', '#4169e1', '#20b2aa', '#ff6347']
                    explode = [0.1 if p == max(percentages) else 0 for p in percentages]  # Explode the largest slice
                    
                    # Create the pie chart with better styling
                    wedges, texts, autotexts = plt.pie(percentages, explode=explode, labels=directions, colors=colors, 
                            autopct='%1.1f%%', shadow=True, startangle=90,
                            textprops={'fontsize': 12, 'fontweight': 'bold'})
                    
                    # Enhance the pie chart with a legend and additional styling
                    plt.legend(wedges, [f"{d} ({c} vehicles)" for d, c in zip(directions, counts)],
                              title="Traffic Distribution",
                              loc="center left",
                              bbox_to_anchor=(1, 0, 0.5, 1))
                    
                    # Make the percentage text more visible
                    for autotext in autotexts:
                        autotext.set_color('white')
                        autotext.set_fontsize(10)
                        autotext.set_fontweight('bold')
                    
                    # Add a title with better styling
                    plt.title('Percentage Distribution of Traffic', fontsize=16, 
                              fontweight='bold', pad=20, color='#483d8b')
                    
                    # Save the pie chart to a BytesIO object
                    pie_buf = io.BytesIO()
                    plt.savefig(pie_buf, format='png', dpi=120, bbox_inches='tight')
                    pie_buf.seek(0)
                    plt.close()
                    
                    # Add the pie chart to the PDF
                    pdf.image(pie_buf, x=20, y=None, w=170)
                    
                    # Add a detailed table with traffic statistics
                    pdf.ln(10)
                    pdf.set_font('Arial', 'B', 12)
                    pdf.set_fill_color(106, 90, 205)  # Slate blue
                    pdf.set_text_color(255, 255, 255)
                    pdf.cell(0, 10, 'Detailed Traffic Distribution', 0, 1, 'C')
                    
                    # Table header
                    pdf.ln(5)
                    pdf.set_fill_color(230, 230, 250)  # Light purple
                    pdf.set_text_color(76, 40, 130)  # Deep purple text
                    pdf.set_font('Arial', 'B', 11)
                    
                    # Center the table
                    table_width = 160
                    table_x = (210 - table_width) / 2
                    
                    pdf.set_x(table_x)
                    pdf.cell(table_width/3, 10, 'Direction', 1, 0, 'C', 1)
                    pdf.cell(table_width/3, 10, 'Vehicles', 1, 0, 'C', 1)
                    pdf.cell(table_width/3, 10, 'Percentage', 1, 1, 'C', 1)
                    
                    # Table data with alternating row colors
                    pdf.set_font('Arial', '', 10)
                    pdf.set_text_color(0, 0, 0)
                    
                    row_count = 0
                    for direction, data in direction_stats.items():
                        # Alternate row colors
                        if row_count % 2 == 0:
                            pdf.set_fill_color(248, 248, 255)  # Ghost white
                        else:
                            pdf.set_fill_color(240, 240, 250)  # Lighter purple
                        
                        count = data[0] if isinstance(data, tuple) else data
                        percentage = data[1] if isinstance(data, tuple) else (count/sum(counts)*100)
                        
                        pdf.set_x(table_x)
                        pdf.cell(table_width/3, 8, direction, 1, 0, 'C', 1)
                        pdf.cell(table_width/3, 8, str(count), 1, 0, 'C', 1)
                        pdf.cell(table_width/3, 8, f"{percentage:.1f}%", 1, 1, 'C', 1)
                        row_count += 1
                    
                    # Add total row with distinct styling
                    pdf.set_x(table_x)
                    pdf.set_font('Arial', 'B', 10)
                    pdf.set_fill_color(106, 90, 205)  # Slate blue
                    pdf.set_text_color(255, 255, 255)
                    pdf.cell(table_width/3, 8, 'Total', 1, 0, 'C', 1)
                    pdf.cell(table_width/3, 8, str(sum(counts)), 1, 0, 'C', 1)
                    pdf.cell(table_width/3, 8, "100.0%", 1, 1, 'C', 1)
                    
                    # Add analysis of traffic distribution
                    pdf.ln(10)
                    pdf.set_text_color(0, 0, 0)
                    pdf.set_font('Arial', '', 10)
                    
                    # Find the busiest and least busy directions
                    busiest_dir = max(direction_stats.items(), key=lambda x: x[1][0] if isinstance(x[1], tuple) else x[1])[0]
                    least_busy_dir = min(direction_stats.items(), key=lambda x: x[1][0] if isinstance(x[1], tuple) else x[1])[0]
                    
                    pdf.multi_cell(0, 6, f"The traffic distribution analysis shows that the {busiest_dir} direction experienced the highest volume of traffic, while the {least_busy_dir} direction had the lowest traffic volume. This information is crucial for optimizing signal timing to accommodate varying traffic demands across different approaches to the intersection.", 0, 'L')
                    
                    pdf.ln(5)
                    pdf.multi_cell(0, 6, "The adaptive traffic signal system dynamically adjusted green time allocations based on these traffic patterns, resulting in more efficient overall traffic flow compared to traditional fixed-time signal systems.", 0, 'L')
        
        except Exception as e:
            print(f"Error creating traffic distribution summary: {e}")
            # Continue without the traffic distribution summary if there's an error
        
        # Add a conclusion page
        pdf.add_page()
        pdf.set_fill_color(76, 40, 130)  # Deep purple
        pdf.rounded_rect(10, pdf.get_y(), 190, 10, 3, 'F')
        pdf.set_text_color(255, 255, 255)
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, 'Simulation Conclusions', 0, 1, 'C')
        pdf.ln(10)
        
        # Add conclusion content
        pdf.set_text_color(0, 0, 0)
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 8, 'Key Findings:', 0, 1, 'L')
        pdf.ln(2)
        
        # Extract some key metrics for the conclusion
        total_vehicles = 0
        emergency_count = 0
        fuel_saved = 0
        co2_reduced = 0
        
        for section in sections:
            if "TRAFFIC FLOW STATISTICS" in section and "Total Vehicles Processed:" in section:
                for line in section.split('\n'):
                    if "Total Vehicles Processed:" in line:
                        try:
                            total_vehicles = int(line.split(':')[1].strip())
                        except:
                            pass
            elif "EMERGENCY VEHICLE STATISTICS" in section and "Emergency Vehicles Processed:" in section:
                for line in section.split('\n'):
                    if "Emergency Vehicles Processed:" in line:
                        try:
                            emergency_count = int(line.split(':')[1].strip())
                        except:
                            pass
            elif "ENVIRONMENTAL IMPACT" in section:
                for line in section.split('\n'):
                    if "Estimated Fuel Saved:" in line:
                        try:
                            fuel_saved = float(line.split(':')[1].strip().split()[0])
                        except:
                            pass
                    elif "Estimated CO2 Reduction:" in line:
                        try:
                            co2_reduced = float(line.split(':')[1].strip().split()[0])
                        except:
                            pass
        
        # Create a summary box with key metrics
        pdf.set_fill_color(248, 248, 255)  # Ghost white
        pdf.rounded_rect(20, pdf.get_y(), 170, 50, 5, 'F')
        
        # Add metrics in a more visual way
        pdf.set_font('Arial', '', 10)
        pdf.set_y(pdf.get_y() + 5)
        
        # Total vehicles
        pdf.set_x(30)
        pdf.set_font('Arial', 'B', 11)
        pdf.set_text_color(76, 40, 130)  # Deep purple
        pdf.cell(80, 8, 'Total Vehicles:', 0, 0, 'L')
        pdf.set_font('Arial', 'B', 11)
        pdf.cell(80, 8, f"{total_vehicles}", 0, 1, 'L')
        
        # Emergency vehicles
        pdf.set_x(30)
        pdf.set_font('Arial', 'B', 11)
        pdf.set_text_color(220, 20, 60)  # Crimson
        pdf.cell(80, 8, 'Emergency Vehicles:', 0, 0, 'L')
        pdf.set_font('Arial', 'B', 11)
        pdf.cell(80, 8, f"{emergency_count}", 0, 1, 'L')
        
        # Fuel saved
        pdf.set_x(30)
        pdf.set_font('Arial', 'B', 11)
        pdf.set_text_color(46, 139, 87)  # Sea green
        pdf.cell(80, 8, 'Fuel Saved:', 0, 0, 'L')
        pdf.set_font('Arial', 'B', 11)
        pdf.cell(80, 8, f"{fuel_saved:.2f} liters", 0, 1, 'L')
        
        # CO2 reduced
        pdf.set_x(30)
        pdf.set_font('Arial', 'B', 11)
        pdf.set_text_color(70, 130, 180)  # Steel blue
        pdf.cell(80, 8, 'CO2 Reduced:', 0, 0, 'L')
        pdf.set_font('Arial', 'B', 11)
        pdf.cell(80, 8, f"{co2_reduced:.2f} kg", 0, 1, 'L')
        
        # Add some analysis text
        pdf.ln(10)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font('Arial', '', 10)
        pdf.multi_cell(0, 6, 'The simulation demonstrates the effectiveness of the adaptive traffic signal system in optimizing traffic flow and reducing environmental impact. The system successfully prioritized emergency vehicles while maintaining efficient overall traffic management.', 0, 'L')
        
        pdf.ln(5)
        pdf.multi_cell(0, 6, 'The direction-based analysis shows variations in traffic volume across different approaches to the intersection, highlighting the importance of adaptive signal timing to accommodate these differences.', 0, 'L')
        
        pdf.ln(5)
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(0, 8, 'Environmental Benefits:', 0, 1, 'L')
        pdf.set_font('Arial', '', 10)
        pdf.multi_cell(0, 6, f'The adaptive system resulted in estimated fuel savings of {fuel_saved:.2f} liters and CO2 reduction of {co2_reduced:.2f} kg, demonstrating the environmental benefits of optimized traffic management.', 0, 'L')
        
        # Save the PDF
        pdf.output(pdf_file)
        
        # Open the PDF file automatically
        if platform.system() == 'Windows':
            os.startfile(pdf_file)
        elif platform.system() == 'Darwin':  # macOS
            subprocess.call(('open', pdf_file))
        else:  # Linux
            subprocess.call(('xdg-open', pdf_file))
        
        print("PDF report generated at: {0}".format(pdf_file))
        return "PDF exported to {0}".format(os.path.basename(pdf_file))
        
    except ImportError as e:
        print("Could not generate PDF report: {0}".format(str(e)))
        return "Error: PDF library not found. Installing..."
    except Exception as e:
        print("Error exporting to PDF: {0}".format(str(e)))
        return "Error: {0}".format(str(e))
# Function to save simulation results
def save_simulation_results():
    try:
        # Create results directory if it doesn't exist
        base_path = os.path.dirname(os.path.abspath(__file__))
        results_dir = os.path.join(base_path, 'results')
        if not os.path.exists(results_dir):
            os.makedirs(results_dir)
        
        # Create reports directory if it doesn't exist
        reports_dir = os.path.join(base_path, 'reports')
        if not os.path.exists(reports_dir):
            os.makedirs(reports_dir)
        
        # Generate timestamp for filename
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        
        # Save statistics to CSV
        stats_file = os.path.join(results_dir, 'traffic_stats_{0}.csv'.format(timestamp))
        with open(stats_file, 'w') as f:
            f.write("Time,Total Vehicles,Emergency Vehicles,Fuel Saved,CO2 Reduced")
            for direction in directionNumbers.values():
                f.write(",{0} Vehicles".format(direction.capitalize()))
            f.write("\n")
            
            for i in range(len(stats_data['time'])):
                f.write("{0},{1},{2},{3:.2f},{4:.2f}".format(
                    stats_data['time'][i],
                    stats_data['total_vehicles'][i],
                    stats_data['emergency_vehicles'][i],
                    stats_data['fuel_saved'][i],
                    stats_data['co2_reduced'][i]
                ))
                for direction in directionNumbers.values():
                    if i < len(stats_data['vehicles_passed'][direction]):
                        f.write(",{0}".format(stats_data['vehicles_passed'][direction][i]))
                    else:
                        f.write(",0")
                f.write("\n")
        
        # Save graphs as images
        traffic_flow_graph = create_traffic_flow_graph()
        if traffic_flow_graph:
            pygame.image.save(traffic_flow_graph, os.path.join(results_dir, 'traffic_flow_{0}.png'.format(timestamp)))
        
        emergency_graph = create_emergency_response_graph()
        if emergency_graph:
            pygame.image.save(emergency_graph, os.path.join(results_dir, 'emergency_vehicles_{0}.png'.format(timestamp)))
        
        signal_timing_graph = create_signal_timing_graph()
        if signal_timing_graph:
            pygame.image.save(signal_timing_graph, os.path.join(results_dir, 'signal_timing_{0}.png'.format(timestamp)))
        
        total_vehicles_graph = create_total_vehicles_graph()
        if total_vehicles_graph:
            pygame.image.save(total_vehicles_graph, os.path.join(results_dir, 'total_vehicles_{0}.png'.format(timestamp)))
        
        # Save fuel emission graph
        fuel_emission_graph = create_fuel_emission_graph()
        if fuel_emission_graph:
            pygame.image.save(fuel_emission_graph, os.path.join(results_dir, 'fuel_emission_{0}.png'.format(timestamp)))
        
        # Calculate total vehicles from the last entry in stats_data
        total_vehicles = stats_data['total_vehicles'][-1] if stats_data['total_vehicles'] else 0
        
        # Save detailed report
        report_file = os.path.join(reports_dir, 'traffic_report_{0}.txt'.format(timestamp))
        with open(report_file, 'w') as f:
            f.write("=================================================================\n")
            f.write("                TRAFFIC SIMULATION ANALYSIS REPORT               \n")
            f.write("=================================================================\n")
            f.write("Report Generated: {0}\n".format(time.strftime('%Y-%m-%d %H:%M:%S')))
            f.write("Simulation Duration: {0} seconds\n\n".format(timeElapsed))
            
            f.write("TRAFFIC FLOW STATISTICS\n")
            f.write("-----------------------\n")
            f.write("Total Vehicles Processed: {0}\n".format(total_vehicles))
            f.write("Vehicles Per Second: {0:.2f}\n\n".format(total_vehicles/max(1, timeElapsed)))
            
            f.write("DIRECTION STATISTICS\n")
            f.write("-------------------\n")
            for i, direction in directionNumbers.items():
                vehicles_crossed = vehicles[direction]['crossed']
                percentage = (vehicles_crossed / max(1, total_vehicles)) * 100
                avg_green_time = signals[i].totalGreenTime / max(1, timeElapsed) * timeElapsed
                
                f.write("{0} Direction:\n".format(direction.upper()))
                f.write("  - Vehicles Passed: {0}\n".format(vehicles_crossed))
                f.write("  - Percentage of Total: {0:.1f}%\n".format(percentage))
                f.write("  - Average Green Time: {0:.1f} seconds\n".format(avg_green_time))
            
            f.write("\nEMERGENCY VEHICLE STATISTICS\n")
            f.write("---------------------------\n")
            f.write("Emergency Vehicles Processed: {0}\n\n".format(emergencyVehicleCount))
            
            f.write("ENVIRONMENTAL IMPACT\n")
            f.write("-------------------\n")
            f.write("Estimated Fuel Saved: {0:.2f} liters\n".format(total_fuel_saved))
            f.write("Estimated CO2 Reduction: {0:.2f} kg\n\n".format(total_co2_reduction))
            
            f.write("SIGNAL EFFICIENCY\n")
            f.write("----------------\n")
            for i, direction in directionNumbers.items():
                green_time = signals[i].totalGreenTime
                efficiency = vehicles[direction]['crossed'] / max(1, green_time)
                
                f.write("{0} Signal:\n".format(direction.upper()))
                f.write("  - Total Green Time: {0} seconds\n".format(green_time))
                f.write("  - Efficiency: {0:.2f} vehicles/second of green\n".format(efficiency))
        
        # Note: PDF generation is now handled in the button click event
        # to avoid circular imports or function calls
        
        return "Results saved successfully"
    
    except Exception as e:
        print("Error saving results: {0}".format(e))
        return "Error saving results: {0}".format(str(e)[:20])
# Start the simulation
if __name__ == "__main__":
    # Create sounds directory if it doesn't exist
    base_path = os.path.dirname(os.path.abspath(__file__))
    sounds_dir = os.path.join(base_path, 'sounds')
    if not os.path.exists(sounds_dir):
        os.makedirs(sounds_dir)
        print(f"Created sounds directory at {sounds_dir}")
        print("Please add ambulance_siren.wav to this directory")
    
    Main()