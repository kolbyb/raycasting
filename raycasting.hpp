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
        results_available = false;
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