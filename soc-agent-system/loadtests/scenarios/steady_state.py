"""
Steady-state load test shape for SOC Agent System.

Maintains a constant load of 10 users with spawn rate 2 for 5 minutes.
This simulates normal day-to-day SOC operations.

Usage:
    locust -f locustfile.py,scenarios/steady_state.py --host=http://localhost:8000
"""

import math

from locust import LoadTestShape


class SteadyStateShape(LoadTestShape):
    """Constant load shape: 10 users, spawn rate 2, 5 minutes duration.

    Timeline:
        0s   -> Ramp up to 10 users at spawn rate 2
        300s -> Test ends

    This shape is useful for:
        - Baseline performance measurement
        - Identifying memory leaks over time
        - Measuring steady-state response times
    """

    # Configuration
    target_users = 10
    spawn_rate = 2
    duration_seconds = 5 * 60  # 5 minutes

    def tick(self):
        """Return (user_count, spawn_rate) or None to stop.

        Returns:
            Tuple of (user_count, spawn_rate) or None when test is complete.
        """
        run_time = self.get_run_time()

        if run_time > self.duration_seconds:
            return None

        return self.target_users, self.spawn_rate

