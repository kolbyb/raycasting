#pragma once
#include <atomic>
#include <condition_variable>
#include <memory>
#include <thread>
#include <iostream>
#include "geometry.hpp"

class World : public std::enable_shared_from_this<World>
{
public:
    [[nodiscard]] std::shared_ptr<World> get_pointer()
    {
        return shared_from_this();
    }

    std::vector<Segment> walls;
};

std::shared_ptr<World> MakeWorld()
{
    return std::make_shared<World>();
}

class Camera
{
public:
    Camera() = default;
    Camera(const Point location, double direction, double viewing_angle) :
        location(location),
        direction(direction),
        viewing_angle(viewing_angle)
    {
    }

    Point  location = {};
    double direction = 0.0;
    double viewing_angle = 0.0;
    bool   planar_projection = true;

    void try_move(double Distance, World* World)
    {
        const Point Movement = Point(Distance * std::sin(direction), Distance * std::cos(direction));
        const Segment ProposedMove = Segment(location, location + Movement);

        if (!ProposedMove.intersect_list(World->walls).hit)
        {
            location = ProposedMove.end;
        }
    }

    void rotate(double angle)
    {
        direction = std::fmod(direction + angle, math::Pi2);
    }

    [[nodiscard]] std::vector<Ray> rays(int Count) const
    {
        // The idea is that we are creating a line
        // through which to draw the rays, so we get a more correct
        // (not curved) distribution of rays, but we still need
        // to do a height correction later to flatten it out

        const double StartAngle = direction - viewing_angle / 2;
        const double EndAngle = StartAngle + viewing_angle;
        std::vector<Ray> Result;

        Result.reserve(Count);
        if (planar_projection)
        {
            const Point PlaneStart = location + Point(std::sin(StartAngle), std::cos(StartAngle));
            const Point PlaneEnd = location + Point(std::sin(EndAngle), std::cos(EndAngle));
            const Point Delta = (PlaneEnd - PlaneStart) / double(Count);

            for (int Current = 0; Current < Count; ++Current)
            {
                const Point PlanePoint = Point(PlaneStart.x + (Delta.x * Current), PlaneStart.y + (Delta.y * Current));
                const Segment ray_segment = Segment(location, PlanePoint);

                Result.push_back(ray_segment.to_ray());
            }
        }
        else
        {
            const double AngleSlice = viewing_angle / Count;

            for (int Current = 0; Current < Count; ++Current)
            {
                Result.push_back(Ray(location, StartAngle + AngleSlice * Current));
            }
        }
        return Result;
    }
};

class RayCastWorker
{
public:
    RayCastWorker(std::shared_ptr<World> world) :
        world(world)
    {
        thread = std::thread(&RayCastWorker::work, this);
    }
    ~RayCastWorker()
    {
        stop();
    }

    void stop()
    {
        if (running)
        {
            running = false;
            set_work({});
            thread.join();
        }
    }

    void set_work(const std::vector<Segment>& RaySegments)
    {
        assert(!work_available);
        ray_segments = RaySegments;
        work_available = true;
        work_condition.notify_one();
    }

    [[nodiscard]] const std::vector<IntersectResult> get_results()
    {
        auto Lock = std::unique_lock(mutex);
        work_condition.wait(Lock, [this](){ return results_available; });
        return results;
    }

private:
    void do_work()
    {
        std::vector<IntersectResult> Results;

        Results.reserve(ray_segments.size());

        for (const Segment& RaySegment : ray_segments)
        {
            Results.push_back(RaySegment.intersect_list(world->walls));
        }
        // Move our results
        {
            auto Lock = std::lock_guard(mutex);
            results = std::move(Results);
        }
        results_available = true;
        work_condition.notify_one();
    }

    void work()
    {
        while (running)
        {
            {
                auto Lock = std::unique_lock(mutex);
                work_condition.wait(Lock, [this](){ return work_available; });
                work_available = false;
            }
            results_available = false;
            do_work();
        }
    }

    // Work
    std::vector<IntersectResult> results = {};
    std::vector<Segment>         ray_segments = {};
    // Signalling
    std::mutex                   mutex;
    std::condition_variable      work_condition = {};
    bool                         work_available = false;
    bool                         results_available = false;
    // Context
    std::shared_ptr<World>       world = nullptr;
    // Thread
    std::atomic_bool             running = true;
    std::thread                  thread = {};
};