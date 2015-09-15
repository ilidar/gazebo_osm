#!/usr/bin/env python
import sys

sys.path.insert(0, 'source')
import os
import numpy as np
from lxml import etree
import argparse
from dict2sdf import GetSDF
from osm2dict import Osm2Dict
from getOsmFile import getOsmFile
from laneBoundaries import LaneBoundaries
from catmull_rom_spline import catmull_rom
from createStageFiles import StageWorld

TIMER = 1


def tic():
    # Homemade version of matlab tic and toc functions
    import time
    global startTime_for_tictoc
    startTime_for_tictoc = time.time()


def toc():
    import time
    if 'startTime_for_tictoc' in globals():
        print("| Elapsed time: " + str(time.time()
                                       - startTime_for_tictoc)
              + " sec")
    else:
        print
        "Toc: start time not set"


if TIMER:
    tic()

parser = argparse.ArgumentParser()
parser.add_argument('-f', '--outFile',
                    help='Output file name', type=str, default='outFile.sdf')
parser.add_argument('-o', '--osmFile', help='Name of the osm file generated',
                    type=str,
                    default='map.osm')
parser.add_argument('-O', '--inputOsmFile', help='Name of the Input osm file',
                    type=str,
                    default='')
parser.add_argument('--stage',
                    help='Generate Stage World',
                    action='store_true')
parser.add_argument('--name', help='Name of stage output name',
                    type=str,
                    default='osm-map')
parser.add_argument('-i', '--imageFile',
                    help='Generate and name .png image of the selected areas',
                    type=str,
                    default='')
parser.add_argument('-d', '--directory',
                    help='Output directory',
                    type=str,
                    default='./')
parser.add_argument('-l', '--lanes',
                    help='export image with lanes',
                    action='store_true')
parser.add_argument('-B', '--boundingbox',
                    help=('Give the bounding box for the area\n' +
                          'Format: MinLon MinLat MaxLon MaxLat'),
                    nargs='*',
                    type=float,
                    default=[-122.0129, 37.3596, -122.0102, 37.3614])

parser.add_argument('-r', '--roads',
                    help='Display Roads',
                    action='store_true')

parser.add_argument('-dbg', '--debug',
                    help='Debug Mode. Gazebo may take a while to load with this.',
                    action='store_true')

parser.add_argument('-m', '--models',
                    help='Display models',
                    action='store_true')

parser.add_argument('-b', '--buildings',
                    help='Display buildings',
                    action='store_true')

parser.add_argument('-a', '--displayAll',
                    help='Display roads and models',
                    action='store_true')
parser.add_argument('--interactive',
                    help='Starts the interactive version of the program',
                    action='store_true')

args = parser.parse_args()

flags = []

if args.buildings:
    flags.append('b')

if args.models:
    flags.append('m')

if args.roads:
    flags.append('r')

if args.lanes:
    flags.append('l')

if not (args.roads or args.models or args.buildings) or args.displayAll:
    flags.append('a')

if not os.path.exists(args.directory):
    os.makedirs(args.directory)

args.osmFile = args.directory + args.osmFile
args.outFile = args.directory + args.outFile

osmDictionary = {}

if args.interactive:
    print("\nPlease enter the latitudnal and logitudnal" +
          " coordinates of the area or select from" +
          " default by hitting return twice \n")

    startCoords = raw_input("Enter starting coordinates: " +
                            "[lon lat] :").split(' ')
    endCoords = raw_input("Enter ending coordnates: [lon lat]: ").split(' ')

    if (startCoords and endCoords and
                len(startCoords) == 2 and len(endCoords) == 2):

        for incoords in range(2):
            startCoords[incoords] = float(startCoords[incoords])
            endCoords[incoords] = float(endCoords[incoords])

    else:

        choice = raw_input("Default Coordinate options: West El " +
                           "Camino Real Highway, CA (2), Bethlehem," +
                           " PA (default=1): ")

        # if choice != '2':
        #     startCoords = [37.3566, -122.0091]
        #     endCoords = [37.3574, -122.0081]

        # else:
        startCoords = [37.3596, -122.0129]
        endCoords = [37.3614, -122.0102]

    option = raw_input("Do you want to view the area specified? [Y/N]" +
                       " (default: Y): ").upper()

    osmFile = 'map.osm'
    args.boundingbox = [min(startCoords[1], endCoords[1]),
                        min(startCoords[0], endCoords[0]),
                        max(startCoords[1], endCoords[1]),
                        max(startCoords[0], endCoords[0])]

    if option != 'N':
        args.imageFile = 'map.png'

if args.inputOsmFile:
    f = open(args.inputOsmFile, 'r')
    root = etree.fromstring(f.read())
    f.close()
    args.boundingbox = [float(root[0].get('minlon')),
                        float(root[0].get('minlat')),
                        float(root[0].get('maxlon')),
                        float(root[0].get('maxlat'))]
print(' _______________________________')
print('|')
print('| Downloading the osm data ... ')
osmDictionary = getOsmFile(args.boundingbox,
                           args.osmFile, args.inputOsmFile)

# if args.imageFile:
#     if TIMER:
#         tic()
#     print "Building the image file ..."
#     args.imageFile = args.directory + args.imageFile
#     getMapImage(args.osmFile, args.imageFile)
#     if TIMER:
#         toc()

# Initialize the class
osmRoads = Osm2Dict(args.boundingbox[0], args.boundingbox[1],
                    args.boundingbox[2], args.boundingbox[3],
                    osmDictionary, flags)

print('| Extracting the map data for gazebo ...')
# get Road and model details
roadPointWidthMap, modelPoseMap, buildingLocationMap = osmRoads.getMapDetails()
# roadPointWidthMap = osmRoads.getRoadDetails()
print('| Building sdf file ...')
# Initialize the getSdf class
sdfFile = GetSDF()


# Set up the spherical coordinates
sdfFile.addSphericalCoords(osmRoads.getLat(), osmRoads.getLon())

# add Required models
sdfFile.includeModel("sun")
for model in modelPoseMap.keys():
    points = modelPoseMap[model]['points']
    if len(points) > 2:
        sdfFile.addModel(modelPoseMap[model]['mainModel'],
                         model,
                         [points[0, 0], points[1, 0], points[2, 0]])

for building in buildingLocationMap.keys():
    sdfFile.addBuilding(buildingLocationMap[building]['mean'],
                        buildingLocationMap[building]['points'],
                        building,
                        buildingLocationMap[building]['color'])
print('|')
print('|-----------------------------------')
print('| Number of Roads: ' + str(len(roadPointWidthMap.keys())))
print('|-----------------------------------')
# print ('|')

# fig = plt.figure()

lanes = 0

roadLaneSegments = []
centerLaneSegments = []
laneSegmentWidths = []

# Include the roads in the map in sdf file
for idx, road in enumerate(roadPointWidthMap.keys()):
    sdfFile.addRoad(road, roadPointWidthMap[road]['texture'])
    sdfFile.setRoadWidth(roadPointWidthMap[road]['width'], road)
    points = roadPointWidthMap[road]['points']

    print('| Road' + str(idx + 1) + ': ' + road)

    laneSegmentWidths.append(roadPointWidthMap[road]['width'])
    print
    "|  -- Width: ", str(roadPointWidthMap[road]['width'])

    xData = points[0, :]
    yData = points[1, :]

    if len(xData) < 3:
        # print ('Cannot apply spline with [' + str(len(xData)) + '] points. At least 3 needed.')

        x = []
        y = []
        lanePoint = []

        for j in np.arange(len(xData)):
            sdfFile.addRoadPoint([xData[j], yData[j], 0], road)
            lanePoint.append([xData[j], yData[j]])
            x.append(xData[j])
            y.append(yData[j])

        # if len(xData) == 1:
        #     sdfFile.addRoadPoint([xData[0], yData[0], 0], road)
        #     #sdfFile.addRoadDebug([xData[0], yData[0], 0], road)
        #     if len(xData) == 2:
        #         sdfFile.addRoadPoint([xData[1], yData[1], 0], road)
        #         #sdfFile.addRoadDebug([xData[1], yData[1], 0], road)


        roadLaneSegments.append([lanePoint, lanePoint])
        centerLaneSegments.append([x, y])

    else:

        x, y = catmull_rom(xData, yData, 10)

        centerLaneSegments.append([x, y])

        lanes = LaneBoundaries(x, y)

        # [lanePointsA, lanePointsB]  = lanes.createLanes(6)

        # roadLaneSegments.append([lanePointsA, lanePointsB])

        # xPointsA = []
        # yPointsA = []

        # xPointsB = []
        # yPointsB = []

        # for i in range(len(lanePointsA)/2):
        #     xPointsA.append(lanePointsA[i*2][0])
        #     yPointsA.append(lanePointsA[i*2][1])
        #     #sdfFile.addLeftLaneDebug([lanePointsA[i*2][0], lanePointsA[i*2][1], 0], road)

        #     xPointsB.append(lanePointsB[i*2][0])
        #     yPointsB.append(lanePointsB[i*2][1])
        #     #sdfFile.addRightLaneDebug([lanePointsB[i*2][0], lanePointsB[i*2][1], 0], road)

        #### Debug
        # plt.plot(xData, yData, 'bo', x, y, 'r-', xPointsA, yPointsA, 'g-', xPointsB, yPointsB, 'g-')
        # plt.plot(xPointsA, yPointsA, 'g-', xPointsB, yPointsB, 'g-')
        # plt.plot(xData, yData, 'ro-', x, y, 'b+')
        # plt.legend(['data', 'catmull'], loc='best')
        ##plt.plot(x, y, 'b+')
        # plt.show()
        #### Debug


        # lanes.saveImage(size, lanePointsA, lanePointsB)

        # if idx == len(roadPointWidthMap.keys())-1:
        #     lanes.showImage()

        for point in range(len(x)):
            sdfFile.addRoadPoint([x[point], y[point], 0], road)
            # sdfFile.addRoadDebug([x[point], y[point], 0], road)

print('|')
print('|-----------------------------------')
print('| Generating the SDF world file...')
sdfFile.writeToFile(args.outFile)

# if args.imageFile:
print('| Generating Image File...')
print('|-----------------------------------')
print('|')
size = osmRoads.getMapSize()
#    args.imageFile = args.directory + args.imageFile
# lanes.makeImage(size, 1, roadLaneSegments, centerLaneSegments, laneSegmentWidths,
#                 args.name + ".png")

print('| Lat Center  = ' + str(osmRoads.getLat()))
print('| Lon Center  = ' + str(osmRoads.getLon()))

if args.stage:
    stage = StageWorld([443, 700], [1300, 4800], [-45.12, 14.4334], [4.2, 444.355])

    stage.createStageSetup(args.name)

# plt.show()

if TIMER:
    toc()

print('|______________________________')
print('')
