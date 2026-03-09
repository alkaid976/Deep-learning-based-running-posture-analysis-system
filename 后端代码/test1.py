import cv2
import mediapipe as mp

print("测试开始...")
# 测试OpenCV
cap = cv2.VideoCapture(0)
ret, frame = cap.read()
print(f"摄像头读取: {ret}")

# 测试MediaPipe
mp_pose = mp.solutions.pose
pose = mp_pose.Pose()
print("MediaPipe初始化成功")

cap.release()
print("测试完成")