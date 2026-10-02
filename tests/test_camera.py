"""Проверки движения камеры без Minecraft и реальных задержек."""
import threading
import unittest
from unittest.mock import patch

from builder.camera import Camera


class CameraTests(unittest.TestCase):
    def test_command_latency_is_part_of_frame(self):
        now = [0.0]
        def sleep(seconds):
            now[0] += seconds
        with patch('builder.camera.time.monotonic', side_effect=lambda: now[0]), patch('builder.camera.time.sleep', side_effect=sleep):
            cam = Camera()
            stamps = []
            for t in cam._frames(0.2):
                stamps.append(now[0])
                now[0] += 0.02
            self.assertAlmostEqual(stamps[1] - stamps[0], 0.05)
            self.assertEqual(t, 1.0)

    def test_interrupted_orbit_keeps_actual_angle(self):
        cam = Camera()
        cam.name = 'Player'
        cam.speed = 8
        stop = threading.Event()
        def frame(*args):
            stop.set()
        cam._tp = frame
        cam.orbit((0, 0, 0), (10, 20, 10), 10, stop=stop)
        self.assertAlmostEqual(cam.angle, -60, places=2)

    def test_yaw_crosses_boundary_by_shortest_path(self):
        cam = Camera()
        cam.rotation = (179, 0)
        yaw, _ = cam._look((0, 0, 0), (0.01, 0, -1))
        self.assertLess(abs(yaw - 179), 2)

    def test_transition_reaches_exact_pose(self):
        cam = Camera()
        cam.pos, cam.rotation = (0, 0, 0), (0, 0)
        cam._frames = lambda *args: iter((0, 0.5, 1))
        poses = []
        cam._pose = lambda pos, rot: poses.append((pos, rot))
        cam.transition((10, 20, 30), (10, 20, 40))
        self.assertEqual(poses[0][0], (0, 0, 0))
        self.assertEqual(poses[-1][0], (10, 20, 30))

if __name__ == '__main__':
    unittest.main()
