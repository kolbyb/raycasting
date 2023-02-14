import cppyy
cppyy.include('geometry.cpp')
from cppyy.gbl import Point, Line, Ray, IntersectResult, Segment, IntersectRayResult, intersect_segment_cpp, intersect_ray_cpp

def intersect_segment(segment: Segment, segments: list[Segment]):
    result: IntersectRayResult = intersect_segment_cpp(segment, segments)
    return [] if not result.hit else [(result.distance, result.point, result.segment)]

def intersect_ray(ray: Ray, segments: list[Segment]):
    result: IntersectRayResult = intersect_ray_cpp(ray, segments)
    return [] if not result.hit else [(result.distance, result.point, result.segment)]
