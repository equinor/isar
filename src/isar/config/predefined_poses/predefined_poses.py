from alitra import Frame, Orientation, Pose, Position

# Euler heading to quaternion
# East = 0 deg = (x=0, y=0, z=0, w=1)
# North = 90 deg = (x=0, y=0, z=0.7071, w=0.7071)
# West = 180 deg = (x=0, y=0, z=1, w=0)
# South = 270 deg = (x=0, y=0, z=-0.7071, w=0.7071)

robot_frame = Frame("robot")
asset_frame = Frame("asset")
predefined_poses = {
    #
    # K-lab VG2
    #
    # View from VG2 towards crane
    "20-PT-5583": Pose(
        position=Position(x=20257.979, y=5310.630, z=14.365, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0, w=1, frame=asset_frame),
        frame=asset_frame,
    ),
    # Open area picture of fuse box
    "EJE-342-0231": Pose(
        position=Position(x=20252.559, y=5308.437, z=14.375, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0, w=1, frame=asset_frame),
        frame=asset_frame,
    ),
    # Big valve straight behind the stairs. East heading
    "331-LD-525": Pose(
        position=Position(x=20254.540, y=5311.651, z=14.321, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0, w=1, frame=asset_frame),
        frame=asset_frame,
    ),
    # Small valve close to utility station. East heading
    "344-LD-1024": Pose(
        position=Position(x=20260.593, y=5312.311, z=14.418, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0, w=1, frame=asset_frame),
        frame=asset_frame,
    ),
    #
    # K-lab inlet area
    #
    "334-LD-0225": Pose(
        position=Position(x=1.63, y=1.724, z=0, frame=robot_frame),
        orientation=Orientation(x=0, y=0, z=0.5383686, w=0.8427095, frame=robot_frame),
        frame=robot_frame,
    ),
    "314-LD-1001": Pose(
        position=Position(x=24.853, y=23.761, z=0, frame=robot_frame),
        orientation=Orientation(x=0, y=0, z=0.998122, w=0.0612579, frame=robot_frame),
        frame=robot_frame,
    ),
    "346-LD-1073": Pose(
        position=Position(x=25.005, y=23.607, z=0, frame=robot_frame),
        orientation=Orientation(x=0, y=0, z=0.9995287, w=-0.0306988, frame=robot_frame),
        frame=robot_frame,
    ),
    "314-PI-001": Pose(
        position=Position(x=25.041, y=23.682, z=0, frame=robot_frame),
        orientation=Orientation(x=0, y=0, z=0.8907533, w=0.4544871, frame=robot_frame),
        frame=robot_frame,
    ),
    "300-LD-0025": Pose(
        position=Position(x=21.279, y=17.392, z=0, frame=robot_frame),
        orientation=Orientation(x=0, y=0, z=0.2006291, w=0.9796673, frame=robot_frame),
        frame=robot_frame,
    ),
    "344-LD-1001": Pose(
        position=Position(x=24.853, y=23.761, z=0, frame=robot_frame),
        orientation=Orientation(x=0, y=0, z=0.998122, w=0.0612579, frame=robot_frame),
        frame=robot_frame,
    ),
    "15-LD-0059": Pose(
        position=Position(x=27.297, y=22.686, z=0, frame=robot_frame),
        orientation=Orientation(x=0, y=0, z=0.9631559, w=0.2689439, frame=robot_frame),
        frame=robot_frame,
    ),
    "345-LD-1004": Pose(
        position=Position(x=20.293, y=20.982, z=0, frame=robot_frame),
        orientation=Orientation(x=0, y=0, z=0.5256679, w=0.8506899, frame=robot_frame),
        frame=robot_frame,
    ),
    # start of narrow passage
    "345-LD-003": Pose(
        position=Position(x=20.994, y=10.3, z=0, frame=robot_frame),
        orientation=Orientation(x=0, y=0, z=0.8963647, w=0.4433175, frame=robot_frame),
        frame=robot_frame,
    ),
    # end of narrow passage
    "345-LD-004": Pose(
        position=Position(x=16.609, y=15.444, z=0, frame=robot_frame),
        orientation=Orientation(x=0, y=0, z=0.999986, w=0.0052963, frame=robot_frame),
        frame=robot_frame,
    ),
    #
    # Compressor area K-lab
    #
    "355-LD-1003": Pose(
        position=Position(x=20248.440, y=5247.118, z=14.450, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=-0.054, w=0.998, frame=asset_frame),
        frame=asset_frame,
    ),
    "313-LD-1111": Pose(
        position=Position(x=20249.830, y=5246.737, z=14.450, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0.999, w=-0.041, frame=asset_frame),
        frame=asset_frame,
    ),
    # 313-LD-1104 and 313-PA-101A has the same pose
    "313-LD-1104": Pose(
        position=Position(x=20250.720, y=5252.582, z=14.450, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0.935, w=0.356, frame=asset_frame),
        frame=asset_frame,
    ),
    # 313-LD-1104 and 313-PA-101A has the same pose
    "313-PA-101A": Pose(
        position=Position(x=20252.860, y=5252.368, z=14.450, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0.935, w=0.357, frame=asset_frame),
        frame=asset_frame,
    ),
    #
    #   Second Floor K-Lab Compressor area
    #
    # 300-LD-0066 and 300-XCV-003 has the same pose
    # Robot Orientation: 90 deg
    "300-LD-0066": Pose(
        position=Position(x=20259.220, y=5241.849, z=16.880, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0.935, w=0.357, frame=asset_frame),
        frame=asset_frame,
    ),
    # 300-LD-0066 and 300-XCV-003 has the same pose
    # Robot Orientation: 90 deg
    "300-XCV-003": Pose(
        position=Position(x=20259.220, y=5241.849, z=16.880, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0.935, w=0.357, frame=asset_frame),
        frame=asset_frame,
    ),
    # Robot Orientation: 0 deg
    "313-LD-1248": Pose(
        position=Position(x=20256.540, y=5243.902, z=16.880, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0.935, w=0.357, frame=asset_frame),
        frame=asset_frame,
    ),
    # Robot Orientation: 0 deg
    "313-FG-136": Pose(
        position=Position(x=20256.470, y=5243.299, z=16.880, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0.935, w=0.357, frame=asset_frame),
        frame=asset_frame,
    ),
    # 313-LD-1177 and 313-LD-1135 has the same pose
    # Robot Orientation: 270 deg
    "313-LD-1177": Pose(
        position=Position(x=20254.740, y=5242.001, z=16.880, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0.935, w=0.357, frame=asset_frame),
        frame=asset_frame,
    ),
    # 313-LD-1177 and 313-LD-1135 has the same pose
    # Robot Orientation: 270 deg
    "313-LD-1135": Pose(
        position=Position(x=20254.740, y=5242.001, z=16.880, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0.935, w=0.357, frame=asset_frame),
        frame=asset_frame,
    ),
    # Robot Orientation: 270 deg
    "313-LD-1133": Pose(
        position=Position(x=20252.960, y=5241.896, z=16.880, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0.935, w=0.357, frame=asset_frame),
        frame=asset_frame,
    ),
    # Robot Orientation: 270 deg
    "313-FG-135": Pose(
        position=Position(x=20252.100, y=5241.975, z=16.880, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0.935, w=0.357, frame=asset_frame),
        frame=asset_frame,
    ),
    # 313-LD-1243 and 313-LD-1242 has the same pose
    # Robot Orientation: 180 deg
    "313-LD-1243": Pose(
        position=Position(x=20256.640, y=5243.246, z=16.880, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0.935, w=0.357, frame=asset_frame),
        frame=asset_frame,
    ),
    # 313-LD-1243 and 313-LD-1242 has the same pose
    # Robot Orientation: 180 deg
    "313-LD-1242": Pose(
        position=Position(x=20256.640, y=5243.246, z=16.880, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0.935, w=0.357, frame=asset_frame),
        frame=asset_frame,
    ),
    # Robot Orientation: 270 deg
    "313-LD-1037": Pose(
        position=Position(x=20254.650, y=5242.229, z=16.880, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0.935, w=0.357, frame=asset_frame),
        frame=asset_frame,
    ),
    # Robot Orientation: 270 deg
    "313-LD-1050": Pose(
        position=Position(x=20252.560, y=5241.928, z=16.880, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0.935, w=0.357, frame=asset_frame),
        frame=asset_frame,
    ),
    # Robot Orientation: 270 deg
    "313-TT-1102C": Pose(
        position=Position(x=20252.250, y=5242.033, z=16.880, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0.935, w=0.357, frame=asset_frame),
        frame=asset_frame,
    ),
    # 313-LD-1241 and 313-LD-1240 has the same pose
    # Robot Orientation: 270 deg
    "313-LD-1241": Pose(
        position=Position(x=20252.210, y=5241.930, z=16.880, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0.935, w=0.357, frame=asset_frame),
        frame=asset_frame,
    ),
    # 313-LD-1241 and 313-LD-1240 has the same pose
    # Robot Orientation: 270 deg
    "313-LD-1240": Pose(
        position=Position(x=20252.210, y=5241.930, z=16.880, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0.935, w=0.357, frame=asset_frame),
        frame=asset_frame,
    ),
    # Robot Orientation: 270 deg
    "313-LD-1056": Pose(
        position=Position(x=20256.470, y=5241.838, z=16.880, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0.935, w=0.357, frame=asset_frame),
        frame=asset_frame,
    ),
    # Robot Orientation: 270 deg
    "313-LD-1060": Pose(
        position=Position(x=20253.920, y=5246.332, z=16.880, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0.935, w=0.357, frame=asset_frame),
        frame=asset_frame,
    ),
    # Robot Orientation: 90 deg
    "313-PT-1012": Pose(
        position=Position(x=20252.940, y=5246.394, z=16.880, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0.935, w=0.357, frame=asset_frame),
        frame=asset_frame,
    ),
    # 313-PT-1061B and 313-LD-1257 has the same pose
    # Robot Orientation: 90 deg
    "313-PT-1016B": Pose(
        position=Position(x=20250.430, y=5246.008, z=16.880, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0.935, w=0.357, frame=asset_frame),
        frame=asset_frame,
    ),
    # 313-PT-1061B and 313-LD-1257 has the same pose
    # Robot Orientation: 90 deg
    "313-LD-1257": Pose(
        position=Position(x=20250.430, y=5246.008, z=16.880, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0.935, w=0.357, frame=asset_frame),
        frame=asset_frame,
    ),
    # 355-LD-1079 Robot orientation 90 degrees
    "355-LD-1079": Pose(
        position=Position(x=20252.630, y=5253.167, z=18.540, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0.935, w=0.357, frame=asset_frame),
        frame=asset_frame,
    ),
    # 331-EV-1009 Robot orientation 90 degrees
    "331-EV-1009": Pose(
        position=Position(x=20255.710, y=5252.991, z=18.540, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0.935, w=0.357, frame=asset_frame),
        frame=asset_frame,
    ),
    # 313-LD-1094 Robot orientation 90 degrees
    "313-LD-1094": Pose(
        position=Position(x=20255.710, y=5252.980, z=18.540, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0.935, w=0.357, frame=asset_frame),
        frame=asset_frame,
    ),
    # 313-LD-1095 Robot orientation 135 degrees
    "313-LD-1095": Pose(
        position=Position(x=20256.860, y=5252.572, z=18.540, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0.935, w=0.357, frame=asset_frame),
        frame=asset_frame,
    ),
    # 313-LD-1213 Robot orientation 180 degrees
    "313-LD-1213": Pose(
        position=Position(x=20257.070, y=5250.289, z=18.540, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0.935, w=0.357, frame=asset_frame),
        frame=asset_frame,
    ),
    # 313-LD-1214 Robot orientation 180 degrees
    "313-LD-1214": Pose(
        position=Position(x=20257.070, y=5250.289, z=18.540, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0.935, w=0.357, frame=asset_frame),
        frame=asset_frame,
    ),
    # 300-LD-1001 Robot orientation 235 degrees. Part above in 4th floor
    "300-LD-1001": Pose(
        position=Position(x=20257.000, y=5248.983, z=18.540, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0.935, w=0.357, frame=asset_frame),
        frame=asset_frame,
    ),
    # 300-LD-1002 Robot orientation 235 degrees. Part above in 4th floor
    "300-LD-1002": Pose(
        position=Position(x=20257.000, y=5248.983, z=18.540, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0.935, w=0.357, frame=asset_frame),
        frame=asset_frame,
    ),
    # 313-JA-001 Robot orientation 270 degrees
    "313-JA-001": Pose(
        position=Position(x=20255.810, y=5248.977, z=18.540, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0.935, w=0.357, frame=asset_frame),
        frame=asset_frame,
    ),
    # 313-HH-001 Robot orientation 0 degrees. Should have photo from other side?
    # Implementation of handling several photos for same part?
    "313-HH-001": Pose(
        position=Position(x=20250.810, y=5249.645, z=18.540, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0.935, w=0.357, frame=asset_frame),
        frame=asset_frame,
    ),
    # EJE-342-1004.08 Robot orientation 0 degrees
    "EJE-342-1004.08": Pose(
        position=Position(x=20251.050, y=5251.786, z=18.540, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0.935, w=0.357, frame=asset_frame),
        frame=asset_frame,
    ),
    # EJE-342-0226.10 Robot orientation 90 degrees
    "EJE-342-0226.10": Pose(
        position=Position(x=20252.070, y=5253.136, z=18.540, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0.935, w=0.357, frame=asset_frame),
        frame=asset_frame,
    ),
    # EJE-342-1004.03 Robot orientation 90 degrees
    "EJE-342-1004.03": Pose(
        position=Position(x=20252.630, y=5253.136, z=18.540, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0.935, w=0.357, frame=asset_frame),
        frame=asset_frame,
    ),
    # 313-KG-001 Robot orientation 90 degrees. Pose on stairs
    "313-KG-001": Pose(
        position=Position(x=20253.900, y=5253.020, z=18.735, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0.935, w=0.357, frame=asset_frame),
        frame=asset_frame,
    ),
    # JBZS-313-021 Robot orientation 270 degrees
    "JBZS-313-021": Pose(
        position=Position(x=20250.000, y=5253.155, z=18.540, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0.935, w=0.357, frame=asset_frame),
        frame=asset_frame,
    ),
    # JBZS-313-024 Robot orientation 315 degrees
    "JBZS-313-024": Pose(
        position=Position(x=20250.160, y=5249.555, z=18.540, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0.935, w=0.357, frame=asset_frame),
        frame=asset_frame,
    ),
    # JBES-313-003 Robot orientation 315 degrees
    "JBES-313-003": Pose(
        position=Position(x=20250.160, y=5249.555, z=18.540, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0.935, w=0.357, frame=asset_frame),
        frame=asset_frame,
    ),
    #
    # AP520 & AP530
    #
    # A-VB20-0292 Car seal valve south heading
    "A-VB20-0292": Pose(
        position=Position(x=309.978, y=108.173, z=536.850, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=-0.7071, w=0.7071, frame=asset_frame),
        frame=asset_frame,
    ),
    # A-VB20-0656 Car seal valve south heading
    "A-VB20-0656": Pose(
        position=Position(x=309.931, y=103.610, z=536.850, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=-0.7071, w=0.7071, frame=asset_frame),
        frame=asset_frame,
    ),
    # A-VB23-0111 Car seal valve east heading
    "A-VB23-0111": Pose(
        position=Position(x=319.502, y=90.022, z=536.850, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0, w=1, frame=asset_frame),
        frame=asset_frame,
    ),
    # A-VB23-0118 Car seal valve west heading
    "A-VB23-0118": Pose(
        position=Position(x=319.865, y=112.225, z=536.850, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=1, w=0, frame=asset_frame),
        frame=asset_frame,
    ),
    # A-VB50-0119 Car seal valve south heading
    "A-VB50-0119": Pose(
        position=Position(x=312.504, y=102.436, z=536.850, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=-0.7071, w=0.7071, frame=asset_frame),
        frame=asset_frame,
    ),
    # A-VB50-0150 Car seal valve east heading
    "A-VB50-0150": Pose(
        position=Position(x=316.401, y=110.011, z=536.850, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0, w=1, frame=asset_frame),
        frame=asset_frame,
    ),
    # A-VB64-0095 Car seal valve south heading
    "A-VB64-0095": Pose(
        position=Position(x=310.027, y=105.676, z=536.850, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=-0.7071, w=0.7071, frame=asset_frame),
        frame=asset_frame,
    ),
    # A-VB64-0096 Car seal valve south heading
    "A-VB64-0096": Pose(
        position=Position(x=310.120, y=104.511, z=536.850, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=-0.7071, w=0.7071, frame=asset_frame),
        frame=asset_frame,
    ),
    # A-VB64-0100 Car seal valve south heading
    "A-VB64-0100": Pose(
        position=Position(x=310.041, y=100.015, z=536.850, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=-0.7071, w=0.7071, frame=asset_frame),
        frame=asset_frame,
    ),
    # A-VB64-0101 Car seal valve south heading
    "A-VB64-0101": Pose(
        position=Position(x=310.041, y=100.015, z=536.850, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=-0.7071, w=0.7071, frame=asset_frame),
        frame=asset_frame,
    ),
    # A-VB23-0147 Car seal valve east heading
    "A-VB23-0147": Pose(
        position=Position(x=333.650, y=112.330, z=536.850, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0, w=1, frame=asset_frame),
        frame=asset_frame,
    ),
    # A-VB23-0392 Car seal valve east heading
    "A-VB23-0392": Pose(
        position=Position(x=334.744, y=90.333, z=536.850, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0, w=1, frame=asset_frame),
        frame=asset_frame,
    ),
    # A-VB23-0539 Car seal valve east heading
    "A-VB23-0539": Pose(
        position=Position(x=335.099, y=112.361, z=536.850, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0, w=1, frame=asset_frame),
        frame=asset_frame,
    ),
    # A-VB23-0398 Car seal valve east heading
    "A-VB23-0398": Pose(
        position=Position(x=343.198, y=87.717, z=536.850, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0, w=1, frame=asset_frame),
        frame=asset_frame,
    ),
    # A-VB23-0545 Car seal valve east heading
    "A-VB23-0545": Pose(
        position=Position(x=343.959, y=112.298, z=536.850, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0, w=1, frame=asset_frame),
        frame=asset_frame,
    ),
    # A-VF50-0153 Car seal valve east heading
    "A-VF50-0153": Pose(
        position=Position(x=338.766, y=101.248, z=536.850, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0, w=1, frame=asset_frame),
        frame=asset_frame,
    ),
    # A-VF50-0154 Car seal valve east heading
    "A-VF50-0154": Pose(
        position=Position(x=337.611, y=109.592, z=536.850, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0, w=1, frame=asset_frame),
        frame=asset_frame,
    ),
    # A-VB23-0183 Car seal valve east heading
    "A-VB23-0183": Pose(
        position=Position(x=341.412, y=83.433, z=536.850, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0, w=1, frame=asset_frame),
        frame=asset_frame,
    ),
    #
    # AP430
    #
    # A-VB20-0039 Car seal valve East
    "A-VB20-0039": Pose(
        position=Position(x=328.343, y=83.986, z=531.850, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0, w=1, frame=asset_frame),
        frame=asset_frame,
    ),
    # A-VG23-0104 Car seal valve South
    "A-VG23-0104": Pose(
        position=Position(x=323.073, y=101.064, z=531.850, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=-0.707, w=0.707, frame=asset_frame),
        frame=asset_frame,
    ),
    # A-VG40-0367 Car seal valve North
    "A-VG40-0367": Pose(
        position=Position(x=332.231, y=92.935, z=531.850, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0.707, w=0.707, frame=asset_frame),
        frame=asset_frame,
    ),
    # A-VM23-0399 Car seal valve South
    "A-VM23-0399": Pose(
        position=Position(x=344.574, y=88.770, z=531.850, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=-0.707, w=0.707, frame=asset_frame),
        frame=asset_frame,
    ),
    # A-VB24-0032 Car seal valve South
    "A-VB24-0032": Pose(
        position=Position(x=341.830, y=90.141, z=531.850, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=-0.707, w=0.707, frame=asset_frame),
        frame=asset_frame,
    ),
    # Home on JS weather deck
    # A-72SP123 Fire extinguisher east heading
    "A-72SP123": Pose(
        position=Position(x=13.453, y=10.317, z=0, frame=robot_frame),
        orientation=Orientation(x=0, y=0, z=0, w=1, frame=robot_frame),
        frame=robot_frame,
    ),
    # Home on JS intermediate deck
    #  Fire extinguisher east heading
    "A-72SP102": Pose(
        position=Position(x=17, y=10.9, z=0, frame=robot_frame),
        orientation=Orientation(x=0, y=0, z=0, w=1, frame=robot_frame),
        frame=robot_frame,
    ),
    #
    # AQ200
    #
    "VG29-4269": Pose(
        position=Position(x=155.5, y=289.8, z=40.8, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=1, w=0, frame=asset_frame),
        frame=asset_frame,
    ),
    "29PT0183": Pose(
        position=Position(x=152.5, y=289.9, z=40.8, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=1, w=0, frame=asset_frame),
        frame=asset_frame,
    ),
    "VB64-4037": Pose(
        position=Position(x=149.25, y=292.16, z=40.8, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=1, w=0, frame=asset_frame),
        frame=asset_frame,
    ),
    "VG53-4024": Pose(
        position=Position(x=151.5, y=286, z=40.8, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=-0.7071, w=0.7071, frame=asset_frame),
        frame=asset_frame,
    ),
    "VF29-4270": Pose(
        position=Position(x=153.35, y=285.56, z=40.8, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0, w=1, frame=asset_frame),
        frame=asset_frame,
    ),
    "VG29-4352": Pose(
        position=Position(x=155.2, y=285.63, z=40.8, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0, w=1, frame=asset_frame),
        frame=asset_frame,
    ),
    "VG29-4249": Pose(
        position=Position(x=154.24, y=282.04, z=40.8, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=1, w=0, frame=asset_frame),
        frame=asset_frame,
    ),
    "29LT0112": Pose(
        position=Position(x=150.88, y=279.84, z=40.8, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=1, w=0, frame=asset_frame),
        frame=asset_frame,
    ),
    "29XU0188": Pose(
        position=Position(x=157.46, y=277.14, z=40.8, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=-0.7071, w=0.7071, frame=asset_frame),
        frame=asset_frame,
    ),
    "VB71-4216": Pose(
        position=Position(x=160.75, y=276.86, z=40.8, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0, w=1, frame=asset_frame),
        frame=asset_frame,
    ),
    "VG29-4337": Pose(
        position=Position(x=160.1, y=278.2, z=40.8, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0.7071, w=0.7071, frame=asset_frame),
        frame=asset_frame,
    ),
    "VG29-4335": Pose(
        position=Position(x=160.07, y=279.07, z=40.8, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0.7071, w=0.7071, frame=asset_frame),
        frame=asset_frame,
    ),
    "VG29-4333": Pose(
        position=Position(x=160.01, y=279.78, z=40.8, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0.7071, w=0.7071, frame=asset_frame),
        frame=asset_frame,
    ),
    "VG29-4331": Pose(
        position=Position(x=160.1, y=280.65, z=40.8, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0.7071, w=0.7071, frame=asset_frame),
        frame=asset_frame,
    ),
    "VG29-4329": Pose(
        position=Position(x=160.12, y=281.56, z=40.8, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0.7071, w=0.7071, frame=asset_frame),
        frame=asset_frame,
    ),
    "VG29-4327": Pose(
        position=Position(x=160.08, y=282.39, z=40.8, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0.7071, w=0.7071, frame=asset_frame),
        frame=asset_frame,
    ),
    "VG29-4325": Pose(
        position=Position(x=160.08, y=282.54, z=40.8, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0.7071, w=0.7071, frame=asset_frame),
        frame=asset_frame,
    ),
    "29PT0214": Pose(
        position=Position(x=161.81, y=282.98, z=40.8, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0, w=1, frame=asset_frame),
        frame=asset_frame,
    ),
    "72SP211": Pose(
        position=Position(x=147.07, y=280.34, z=40.8, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=1, w=0, frame=asset_frame),
        frame=asset_frame,
    ),
    "VG63-4001 ": Pose(
        position=Position(x=148.19, y=287.14, z=40.8, frame=asset_frame),
        orientation=Orientation(x=0, y=0, z=0, w=1, frame=asset_frame),
        frame=asset_frame,
    ),
}
