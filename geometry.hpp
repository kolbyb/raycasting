#pragma once
#include <algorithm>
#include <cmath>
#include <optional>
#include <stdexcept>
#include <vector>

template<typename TType>
constexpr auto Pi()
{
    return TType(3.141592653589793238462);
}

bool IsClose(const double ValueOne, const double ValueTwo, const double Epsilon = 1.0e-9)
{
    return std::fabs(ValueOne - ValueTwo) <= Epsilon;
}

double InRange(const double Min, const double Max, const double Value, const double Epsilon = 1.0e-7)
{
    return (Min - Epsilon) <= Value && Value <= (Max + Epsilon);
}

constexpr double FPi = Pi<double>();
constexpr double F2Pi = Pi<double>() * 2.0;
constexpr double FPi_2 = Pi<double>() * 0.5;
constexpr double FPi_4 = Pi<double>() * 0.25; 

// Forward Declarations
class Point;
struct Line;
class Ray;
class Segment;

class Point
{
public:

    constexpr Point() = default;
    constexpr Point(double x, double y) :
        x(x),
        y(y)
    {
    }

    static Point Forward;
    static Point Right;

    double x = 0.0;
    double y = 0.0;

    [[nodiscard]] double angle() const
    {
        const Point PointNormal = normal();
        const double PointAngle = std::acosf(PointNormal.x);

        return PointNormal.y <= 0.0 ? PointAngle : -PointAngle;
    }

    [[nodiscard]] double cross(const Point& Other) const
    {
        return x * Other.y - y * Other.x;
    }

    [[nodiscard]] double dot(const Point& Other) const
    {
        return x * Other.x + y * Other.y;
    }

    [[nodiscard]] double length() const
    {
        return std::sqrt(dot(*this));
    }

    [[nodiscard]] Point normal() const
    {
        double PointLength = length();

        if (PointLength == 0.0 || IsClose(PointLength, 1.0))
        {
            return *this;
        }
        return Point(x / PointLength, y / PointLength);
    }

    [[nodiscard]] Point operator+(const Point& Other) const
    {
        return Point(x + Other.x, y + Other.y);
    }

    [[nodiscard]] Point operator+=(const Point& Other)
    {
        *this = (*this + Other);
        return *this;
    }

    [[nodiscard]] Point operator-(const Point& Other) const
    {
        return Point(x - Other.x, y - Other.y);
    }

    [[nodiscard]] Point operator-=(const Point& Other)
    {
        *this = (*this - Other);
        return *this;
    }

    [[nodiscard]] Point operator*(const double Other) const
    {
        return Point(x * Other, y * Other);
    }

    [[nodiscard]] friend Point operator*(const double Other, const Point& Point)
    {
        return Point * Other;
    }

    [[nodiscard]] Point operator*=(const double Other)
    {
        *this = (*this * Other);
        return *this;
    }

    [[nodiscard]] Point operator/(const double Other) const
    {
        return Point(x / Other, y / Other);
    }

    [[nodiscard]] Point operator/=(const double Other)
    {
        *this = (*this / Other);
        return *this;
    }

    [[nodiscard]] bool operator==(const Point& Other) const
    {
        return x == Other.x && y == Other.y;
    }

    [[nodiscard]] bool operator!=(const Point& Other) const
    {
        return !(*this == Other);
    }
};

struct Line
{
    Point origin;
    double slope;

    [[nodiscard]] bool operator==(const Line& Other) const
    {
        return origin == Other.origin && IsClose(slope, Other.slope, 1.0e-06);
    }

    [[nodiscard]] bool operator!=(const Line& Other) const
    {
        return !(*this == Other);
    }
};


class Ray
{
public:
    Ray() = default;
    Ray(const Point& start, const double angle) :
        start(start),
        angle(angle)
    {
    }

    static constexpr double DistantPoint = 100.0;

    Point start = Point();
    double angle = 0.0;

    [[nodiscard]] Line to_line() const;
    [[nodiscard]] Point distant_point() const;
    [[nodiscard]] Segment to_segment() const;

    [[nodiscard]] bool operator==(const Ray& Other) const
    {
        return start == Other.start && IsClose(angle, Other.angle, 1.0e-06);
    }

    [[nodiscard]] bool operator!=(const Ray& Other) const
    {
        return !(*this == Other);
    }
};



struct IntersectResult
{
    bool hit = false;
    Point point = {};
};

class Segment
{
public:
    Segment() = default;
    Segment(const Point &start, const Point &end) :
        start(start),
        end(end)
    {
    }

    Point start = Point(0.0, 0.0);
    Point end = Point(1.0, 1.0);

    [[nodiscard]] double angle() const
    {
        return normal().angle();
    }

    [[nodiscard]] double cross() const
    {
        return start.cross(end);
    }

    [[nodiscard]] Point delta() const
    {
        return end - start;
    }

    [[nodiscard]] Point invdelta() const
    {
        return start - end;
    }

    [[nodiscard]] double min_x() const
    {
        return std::min(start.x, end.x);
    }

    [[nodiscard]] double max_x() const
    {

        return std::max(start.x, end.x);
    }

    [[nodiscard]] double min_y() const
    {
        return std::min(start.y, end.y);
    }

    [[nodiscard]] double max_y() const
    {
        return std::max(start.y, end.y);
    }

    [[nodiscard]] Point normal() const
    {
        return delta().normal();
    }

    [[nodiscard]] Point surface_normal() const
    {
        return Point(Point::Forward * normal().x + Point::Right * normal().y);
    }

    [[nodiscard]] double slope() const
    {
        if (start.x == end.x)
        {
            return 1.0e100;
        }
        
        const Point PointDelta = delta();
        return PointDelta.y / PointDelta.x;
    }
    
    [[nodiscard]] Line line() const
    {
        if (start == end)
        {
            throw std::runtime_error("Cannot create Line from identical Segment points");
        }

        return Line{start, slope()};
    }

    [[nodiscard]] bool on_segment(const Point& TestPoint) const
    {
        if (TestPoint == start)
        {
            return true;
        }

        const Segment TestSegment = Segment(start, TestPoint);

        return IsClose(slope(), TestSegment.slope()) and in_bounds(TestPoint);
    }

    [[nodiscard]] bool in_bounds(const Point& TestPoint) const
    {
        return InRange(min_x(), max_x(), TestPoint.x) && InRange(min_y(), max_y(), TestPoint.y);
    }

    [[nodiscard]] Ray to_ray() const
    {
        if (start == end)
        {
            // No possible valid Ray object
            throw std::runtime_error("Cannot create Ray from identical Segment points");
        }

        // Correct from angle above x axis as returned by angle calculation, to angle
        // away from y axis, as is in our coordinate system
        return Ray(start, angle() + FPi_2);
    }
    
    [[nodiscard]] IntersectResult intersect(const Segment& Other) const
    {
        if (!(
            Other.min_x() < max_x()
            && Other.max_x() > min_x()
            && Other.min_y() < max_y()
            && Other.max_y() > min_y()
        ))
        {
            return {};
        }

        const Point a = invdelta();
        const Point b = Other.invdelta();
        const double determinant = a.cross(b);
        
        // The Segments are parallel if the determinant == 0.0
        if (determinant != 0.0)
        {
            const double across = cross();
            const double bcross = Other.cross();
            const Point p = Point(
                (across * b.x - a.x * bcross) / determinant,
                (across * b.y - a.y * bcross) / determinant
            );

            if (Other.in_bounds(p) && in_bounds(p))
            {
                return {true, p};
            }
        }
        
        return {};
    }

    [[nodiscard]] bool operator==(const Segment& Other) const
    {
        return start == Other.start && end == Other.end;
    }

    [[nodiscard]] bool operator!=(const Segment& Other) const
    {
        return !(*this == Other);
    }
};

struct IntersectRayResult
{
    bool hit = false;
    double distance = 0.0;
    Point point = Point();
    Segment segment = Segment();
};

IntersectRayResult intersect_segment_cpp(const Segment& TestSegment, const std::vector<Segment>& Segments)
{
    auto GetDistanceSquared = [](const Point& Delta, double& DistanceSquaredOut) -> double {
        DistanceSquaredOut = Delta.dot(Delta);
        return DistanceSquaredOut;
    };

    IntersectRayResult Result{};
    double BestDistanceSquared = 1.0e+09;
    double DistanceSquared = 1.0e+09;

    for (const Segment& Segment : Segments)
    {
        const IntersectResult Intersect = TestSegment.intersect(Segment);

        if (!Intersect.hit)
        {
            continue;
        }

        if (BestDistanceSquared > GetDistanceSquared(Intersect.point - TestSegment.start, DistanceSquared))
        {
            BestDistanceSquared = DistanceSquared;
            Result = {
                true,
                std::sqrt(DistanceSquared),
                Intersect.point,
                Segment
            };
        }
    }

    return Result;
}

IntersectRayResult intersect_ray_cpp(const Ray& TestRay, const std::vector<Segment>& Segments)
{
    return intersect_segment_cpp(TestRay.to_segment(), Segments);
}