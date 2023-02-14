import cppyy
cppyy.include('geometry.cpp')
from cppyy.gbl import Point, Ray, Segment, IntersectResult
