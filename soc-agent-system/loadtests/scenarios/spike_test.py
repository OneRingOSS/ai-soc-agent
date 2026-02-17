"""
Spike load test shape for SOC Agent System.

Ramps to 50 users over 30 seconds, holds for 2 minutes, then ramps down.
This simulates a sudden attack spike and recovery.

Usage:
    locust -f locustfile.py,scenarios/spike_test.py --host=http://localhost:8000
"""

import math

from locust import LoadTestShape


class SpikeTestShape(LoadTestShape):
    """Spike load shape: ramp to 50 users over 30s, hold 2 min, ramp down.

    Timeline:
        Phase 1 (0-30s):    Ramp up from 0 to 50 users
        Phase 2 (30-150s):  Hold at 50 users (2 minutes)
        Phase 3 (150-180s): Ramp down from 50 to 0 users
        180s:               Test ends

    This shape is useful for:
        - Testing system behavior under sudden load spikes
        - Verifying auto-scaling triggers
        - Measuring recovery time after spike
    """

    # Phase configuration
    ramp_up_duration = 30       # seconds to ramp up
    hold_duration = 2 * 60      # seconds to hold at peak (2 minutes)
    ramp_down_duration = 30     # seconds to ramp down

    peak_users = 50
    spawn_rate = 10  # users per second during ramp phases

    @property
    def total_duration(self):
        """Total test duration in seconds."""
        return self.ramp_up_duration + self.hold_duration + self.ramp_down_duration

    def tick(self):
        """Return (user_count, spawn_rate) or None to stop.

        Returns:
            Tuple of (user_count, spawn_rate) or None when test is complete.
        """
        run_time = self.get_run_time()

        if run_time > self.total_duration:
            return None

        # Phase 1: Ramp up
        if run_time <= self.ramp_up_duration:
            progress = run_time / self.ramp_up_duration
            current_users = max(1, math.ceil(self.peak_users * progress))
            return current_users, self.spawn_rate

        # Phase 2: Hold at peak
        if run_time <= self.ramp_up_duration + self.hold_duration:
            return self.peak_users, self.spawn_rate

        # Phase 3: Ramp down
        elapsed_ramp_down = run_time - self.ramp_up_duration - self.hold_duration
        progress = elapsed_ramp_down / self.ramp_down_duration
        current_users = max(1, math.ceil(self.peak_users * (1 - progress)))
        return current_users, self.spawn_rate

