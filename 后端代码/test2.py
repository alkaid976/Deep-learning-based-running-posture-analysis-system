import cv2
import mediapipe as mp
import matplotlib.pyplot as plt

# 导入solution
mp_pose = mp.solutions.pose

# 导入绘图函数
mp_drawing = mp.solutions.drawing_utils

# 导入模型
pose = mp_pose.Pose(
    static_image_mode=True,  # 静态图片 or 连续帧
    model_complexity=2,  # 模型复杂度 0最快 2最好
    smooth_landmarks=True,  # 是否平滑关键点
    min_detection_confidence=0.5,  # 置信度阈值
    min_tracking_confidence=0.8  # 追踪阈值
)
img = cv2.imread('data/333.png')

img_RGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

a = []
results = pose.process(img_RGB)
for i in [8, 11, 12, 24, 26, 28, 32]:
    # a.append(results.pose_landmarks.landmark[i].visibility)
    print(results.pose_landmarks.landmark[i].visibility)
# print(a)
# print(sum(a) / len(a))