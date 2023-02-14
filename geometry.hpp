#pragma once
#include <algorithm>
#include <cmath>
#include <optional>
#include <stdexcept>
#include <vector>

namespace math
{
    namespace details
    {
        template<typename TType>
        constexpr auto Pi()
        {
            return TType(3.141592653589793238462);
        }
    }

    bool IsClose(const double ValueOne, const double ValueTwo, const double Epsilon = 1.0e-9)
    {
        return std::fabs(ValueOne - ValueTwo) <= Epsilon;
    }

    double InRange(const double Min, const double Max, const double Value, const double Epsilon = 1.0e-7)
    {
        return (Min - Epsilon) <= Value && Value <= (Max + Epsilon);
    }

    constexpr double Pi = details::Pi<double>();
    constexpr double Pi2 = details::Pi<double>() * 2.0;
    constexpr double PiOver2 = details::Pi<double>() * 0.5;
    constexpr double PiOver4 = details::Pi<double>() * 0.25; 
}

// Forward Declarations
class Point;
class Ray;
class Segment;
struct IntersectResult;

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

        if (PointLength == 0.0 || math::IsClose(PointLength, 1.0))
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

    [[nodiscard]] Point distant_point() const;
    [[nodiscard]] Segment to_segment() const;

    [[nodiscard]] bool operator==(const Ray& Other) const
    {
        return start == Other.start && math::IsClose(angle, Other.angle, 1.0e-06);
    }

    [[nodiscard]] bool operator!=(const Ray& Other) const
    {
        return !(*this == Other);
    }
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

    [[nodiscard]] double angle() const;
    [[nodiscard]] double cross() const;
    [[nodiscard]] Point delta() const;
    [[nodiscard]] Point invdelta() const;
    [[nodiscard]] double min_x() const;
    [[nodiscard]] double max_x() const;
    [[nodiscard]] double min_y() const;
    [[nodiscard]] double max_y() const;
    [[nodiscard]] Point normal() const;
    [[nodiscard]] Point surface_normal() const;
    [[nodiscard]] double slope() const;
    [[nodiscard]] bool on_segment(const Point& TestPoint) const;
    [[nodiscard]] bool in_bounds(const Point& TestPoint) const;
    [[nodiscard]] Ray to_ray() const;
    [[nodiscard]] IntersectResult intersect(const Segment& Other) const;
    [[nodiscard]] IntersectResult intersect_list(const std::vector<Segment>& Others) const;

    [[nodiscard]] bool operator==(const Segment& Other) const;
    [[nodiscard]] bool operator!=(const Segment& Other) const;

private:
    [[nodiscard]] std::optional<Point> intersect_internal(const Segment& Other) const;
};


struct IntersectResult
{
    Point   point = Point();
    Segment segment;
    double  distance = 0.0;
    bool    hit = false;
};