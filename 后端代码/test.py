import cv2
import mediapipe as mp
import matplotlib.pyplot as plt
from tqdm import tqdm

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

file_path = './data/416.mp4'
cap = cv2.VideoCapture(file_path)
frame_count = 0
while cap.isOpened():
    success, frame = cap.read()
    frame_count += 1
    if not success:
        break
    cap.release()
    cap = cv2.VideoCapture(file_path)

    with tqdm(total=frame_count - 1) as pbar:
        try:
            while cap.isOpened():
                success, frame = cap.read()
                if not success:
                    break

                # 处理帧
                try:
                    results = pose.process(frame)
                    with open('average', 'a', encoding='utf-8') as file:
                        # for i in [7, 11, 12, 23, 25, 27, 31]:
                        for i in [8, 11, 12, 24, 26, 28, 32]:
                            file.write(str(results.pose_landmarks.landmark[i].visibility) + '\n')
                except:
                    print("error")
                    pass

                if success:
                    pbar.update(1)
        except:
            print("中途中断")
            pass

    cv2.destroyAllWindows()
    cap.release()
