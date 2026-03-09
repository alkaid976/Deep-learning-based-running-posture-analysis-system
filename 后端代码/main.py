import sys

import cv2
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QDesktopWidget
import mediapipe as mp
import numpy as np
import traceback
import sys



from window import Ui_MainWindow


# 角度计算函数
def calculate_angle(vector1, vector2):
    # 计算两个向量的点积
    dot_product = np.dot(vector1, vector2)

    # 计算两个向量的模
    norm_v1 = np.linalg.norm(vector1)
    norm_v2 = np.linalg.norm(vector2)

    # 计算两个向量的夹角
    ang = np.arccos(dot_product / (norm_v1 * norm_v2))

    # 转换角度为角度制
    angle_degrees = np.degrees(ang)
    return round(angle_degrees, 2)


# results里存的坐标需要根据图片原始比例还原
def x_restore(c, w):
    return int(c * w)


def y_restore(c, h):
    return int(c * h)


# 将image转换为QImage的格式
def convert2QImage(img):
    height, width, channel = img.shape
    return QImage(img, width, height, width * channel, QImage.Format_RGB888)


# 自定义关键点的颜色和大小
def draw(results, img):
    h = img.shape[0]
    w = img.shape[1]

    if results.pose_landmarks:
        for i in range(33):
            x = int(results.pose_landmarks.landmark[i].x * w)
            y = int(results.pose_landmarks.landmark[i].y * h)

            radius = 10

            if i == 0:  # 鼻尖
                img = cv2.circle(img, (x, y), 5, (0, 0, 255), -1)
            elif i in [11, 12]:  # 肩膀
                img = cv2.circle(img, (x, y), radius, (223, 155, 6), -1)
            elif i in [23, 24]:  # 髋关节
                img = cv2.circle(img, (x, y), radius, (0, 240, 255), -1)
            elif i in [13, 14]:  # 胳膊肘
                img = cv2.circle(img, (x, y), radius, (140, 47, 240), -1)
            elif i in [25, 26]:  # 膝盖
                img = cv2.circle(img, (x, y), radius, (0, 0, 255), -1)
            elif i in [15, 16, 27, 28]:  # 手腕和脚腕
                img = cv2.circle(img, (x, y), radius, (223, 155, 60), -1)
            elif i in [17, 19, 21]:  # 左手
                img = cv2.circle(img, (x, y), radius, (94, 218, 121), -1)
            elif i in [18, 20, 22]:  # 右手
                img = cv2.circle(img, (x, y), radius, (16, 144, 247), -1)
            elif i in [27, 29, 31]:  # 左脚
                img = cv2.circle(img, (x, y), radius, (29, 123, 243), -1)
            elif i in [28, 30, 22]:  # 右脚
                img = cv2.circle(img, (x, y), radius, (193, 182, 255), -1)
            elif i in [9, 10]:  # 嘴
                img = cv2.circle(img, (x, y), 5, (205, 235, 255), -1)
            elif i in [1, 2, 3, 4, 5, 6, 7, 8]:  # 眼部
                img = cv2.circle(img, (x, y), 5, (94, 218, 121), -1)
            else:  # 其他关键点
                img = cv2.circle(img, (x, y), 5, (0, 255, 0), -1)
    return img


# 判断数组中某一数字重复是否超过30%
def check_repeat_percentage(numbers, target):
    # 计算目标数出现的次数
    count = numbers.count(target)
    # 计算数组中元素的总数
    total_count = len(numbers)
    # 计算目标数重复的百分比
    repeat_percentage = (count / total_count) * 100
    # 判断重复的百分比是否超过30%并存储结果
    repeat_check = repeat_percentage >= 30
    # print(repeat_percentage)
    return repeat_check


class VideoShow(QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        super(VideoShow, self).__init__(parent)
        self.setupUi(self)

        # 导入mediapipe
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=True,  # 静态图片 or 连续帧
            model_complexity=2,  # 模型复杂度 0最快 2最好
            smooth_landmarks=True,  # 是否平滑关键点
            min_detection_confidence=0.5,  # 置信度阈值
            min_tracking_confidence=0.8  # 追踪阈值
        )
        self.mp_drawing = mp.solutions.drawing_utils
        self.connection_drawing_spec = self.mp_drawing.DrawingSpec(color=(225, 225, 225), thickness=3)

        self.timer = QTimer(self)
        self.timer.setInterval(1)

        self.videoButton.clicked.connect(self.open_file)
        self.timer.timeout.connect(self.video_pred)

        self.file_path = None
        self.cap = None
        self.video_writer = None
        self.output_path = './result/output_video.mp4'

        self.warning_leg = []
        self.warning_body = []
        self.warning_head = []

    def video_pred(self):

        self.resultLable.setText("正在对跑姿进行分析......")

        # 读取视频中的一帧
        ret, frame = self.cap.read()

        # 判断是否还有return
        if not ret:
            self.timer.stop()
            self.update_result_label()
            if self.video_writer:
                self.video_writer.release()
            self.resultLable.setText(self.resultLable.text() + "视频已保存在" + self.output_path)
        else:
            # 将opencv读取到的帧转换为RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # 将这一帧进行推理 返回的是所有关键点坐标
            results = self.pose.process(rgb_frame)

            # 画出关键点和连线 frame变成画好的三维数组
            self.mp_drawing.draw_landmarks(rgb_frame, results.pose_landmarks,
                                           self.mp_pose.POSE_CONNECTIONS,
                                           connection_drawing_spec=self.connection_drawing_spec)
            # 将关键点自定画出
            drawn_frame = draw(results, rgb_frame)

            h, w = drawn_frame.shape[0], drawn_frame.shape[1]
            # 所用到的坐标点
            if results.pose_landmarks:
                right_hip = results.pose_landmarks.landmark[24]
                right_knee = results.pose_landmarks.landmark[26]
                right_shoulder = results.pose_landmarks.landmark[12]
                left_hip = results.pose_landmarks.landmark[23]
                left_knee = results.pose_landmarks.landmark[25]

                right_hip_x = x_restore(results.pose_landmarks.landmark[24].x, w)
                right_knee_x = x_restore(results.pose_landmarks.landmark[26].x, w)
                right_ankle_x = x_restore(results.pose_landmarks.landmark[28].x, w)
                right_shoulder_x = x_restore(results.pose_landmarks.landmark[12].x, w)
                right_ear_x = x_restore(results.pose_landmarks.landmark[8].x, w)

                left_hip_x = x_restore(results.pose_landmarks.landmark[23].x, w)
                left_knee_x = x_restore(results.pose_landmarks.landmark[25].x, w)
                left_ankle_x = x_restore(results.pose_landmarks.landmark[27].x, w)
                left_shoulder_x = x_restore(results.pose_landmarks.landmark[11].x, w)
                left_ear_x = x_restore(results.pose_landmarks.landmark[7].x, w)

                right_hip_y = y_restore(results.pose_landmarks.landmark[24].y, h)
                right_knee_y = y_restore(results.pose_landmarks.landmark[26].y, h)
                right_ankle_y = y_restore(results.pose_landmarks.landmark[28].y, h)
                right_shoulder_y = y_restore(results.pose_landmarks.landmark[12].y, h)
                right_ear_y = y_restore(results.pose_landmarks.landmark[8].y, h)

                left_hip_y = y_restore(results.pose_landmarks.landmark[23].y, h)
                left_knee_y = y_restore(results.pose_landmarks.landmark[25].y, h)
                left_ankle_y = y_restore(results.pose_landmarks.landmark[27].y, h)
                left_shoulder_y = y_restore(results.pose_landmarks.landmark[11].y, h)
                left_ear_y = y_restore(results.pose_landmarks.landmark[7].y, h)
                # 由关键点坐标计算角度
                if right_shoulder.z < 0:
                    # 向右跑
                    if results.pose_landmarks.landmark[32].x > right_hip.x:
                        # 当脚尖超过髋部时开始计算角度
                        p1 = (right_hip_x, right_hip_y)
                        p2 = (right_knee_x, right_knee_y)
                        p3 = (right_ankle_x, right_ankle_y)
                        v1 = (p1[0] - p2[0], p1[1] - p2[1])
                        v2 = (p3[0] - p2[0], p3[1] - p2[1])
                        angle_leg = calculate_angle(v1, v2)
                        if angle_leg > 165:
                            # 画出那根线
                            drawn_frame = cv2.line(drawn_frame, p2, p3, (225, 0, 0), 10)
                            self.warning_leg.append(1)
                        else:
                            self.warning_leg.append(0)
                else:
                    # 向左跑
                    if results.pose_landmarks.landmark[31].x < left_hip.x:
                        p1 = (left_hip_x, left_hip_y)
                        p2 = (left_knee_x, left_knee_y)
                        p3 = (left_ankle_x, left_ankle_y)
                        v1 = (p1[0] - p2[0], p1[1] - p2[1])
                        v2 = (p3[0] - p2[0], p3[1] - p2[1])
                        angle_leg = calculate_angle(v1, v2)
                        # print(angle_leg)
                        if angle_leg > 165:
                            drawn_frame = cv2.line(drawn_frame, p2, p3, (225, 0, 0), 10)
                            self.warning_leg.append(1)
                        else:
                            self.warning_leg.append(0)

                # 上半身与y轴、头部与上半身角度判断
                # 判断跑步方向，首先保证身体朝跑步方向倾斜 与y轴夹角不超过2-10度
                # 然后保证耳朵、肩膀、髋尽量在一条直线上 耳朵与上半身夹角不超过5度
                if right_shoulder.z < 0:
                    # 向右跑
                    if right_knee.x < right_hip.x:  # 当右腿后摆时，肩部与身体平行，计算准确
                        p1 = (int((right_shoulder_x + left_shoulder_x) / 2), int((right_shoulder_y + left_shoulder_y) / 2))
                        p2 = (right_hip_x, right_hip_y)
                        p3 = (right_hip_x, right_shoulder_y)
                        p4 = (right_ear_x, right_ear_y)
                        v1 = (p1[0] - p2[0], p1[1] - p2[1])
                        v2 = (p3[0] - p2[0], p3[1] - p2[1])
                        v3 = (p4[0] - p2[0], p4[1] - p2[1])
                        angle_body = calculate_angle(v1, v2)
                        angle_head = calculate_angle(v2, v3)
                        if angle_body > 10:  # 身体前倾角度过大
                            self.warning_body.append(1)
                            drawn_frame = cv2.line(drawn_frame, p1, p2, (225, 0, 0), 10)
                        else:
                            self.warning_body.append(0)

                        if angle_head > 10:
                            self.warning_head.append(1)
                            drawn_frame = cv2.line(drawn_frame, p4, p1, (225, 0, 0), 10)
                        else:
                            self.warning_head.append(0)
                elif left_knee.x > left_hip.x:  # 当左腿后摆时，肩部与身体平行，计算准确  # 向左跑
                    p1 = (int((right_shoulder_x + left_shoulder_x) / 2), int((right_shoulder_y + left_shoulder_y) / 2))
                    p2 = (left_hip_x, left_hip_y)
                    p3 = (left_hip_x, left_shoulder_y)
                    p4 = (left_ear_x, left_ear_y)
                    v1 = (p1[0] - p2[0], p1[1] - p2[1])
                    v2 = (p3[0] - p2[0], p3[1] - p2[1])
                    v3 = (p4[0] - p2[0], p4[1] - p2[1])
                    angle_body = calculate_angle(v1, v2)
                    angle_head = calculate_angle(v2, v3)
                    if angle_body > 10:
                        self.warning_body.append(1)
                        drawn_frame = cv2.line(drawn_frame, p1, p2, (225, 0, 0), 10)
                    else:
                        self.warning_body.append(0)

                    if angle_head > 10:
                        self.warning_head.append(1)
                        drawn_frame = cv2.line(drawn_frame, p4, p1, (225, 0, 0), 10)
                    else:
                        self.warning_head.append(0)
            # 将frame从三维数组转换为QImage格式 然后转换为QPixmap格式
            pix_drawn_frame = QPixmap.fromImage(convert2QImage(drawn_frame))

            # 对frame进行等比例缩小或放大以适应QLabel
            scale_width = pix_drawn_frame.width() / self.videoLabel.width()
            scale_height = pix_drawn_frame.height() / self.videoLabel.height()
            scale = max(scale_width, scale_height)
            scaled_frame = pix_drawn_frame.scaled(int(pix_drawn_frame.width() / scale),
                                                  int(pix_drawn_frame.height() / scale))

            # 将处理好的scaled_frame显示在videoLabel中
            self.videoLabel.setPixmap(scaled_frame)
            # 在window.py文件中设置scaled_frame水平居中
            if self.video_writer:
                self.video_writer.write(cv2.cvtColor(rgb_frame, cv2.COLOR_BGR2RGB))

    # 超出限度时显示结果分析
    def update_result_label(self):
        self.resultLable.setText("分析完毕！<br>")

        leg_content = "脚部着地点与身体重心相差太远，会造成刹车效应，进而导致膝盖和脚踝受伤；<br>" + "应尽量提升膝盖，抬起大腿或提高步频<br>"
        body_content = "身体弯腰驼背，过度前倾，会导致腰肌劳损；<br>" + "应挺直身体并略微前倾，打开肩部，挺胸抬头<br>"
        head_content = "头部俯仰角度过大，会导致颈肩部肌肉紧张; <br>" + "应视线水平目视前方，自然挺胸抬头<br>"

        is_warning_leg = check_repeat_percentage(self.warning_leg, 1)
        # print('leg:' + str(self.warning_leg))
        is_warning_body = check_repeat_percentage(self.warning_body, 1)
        # print('body:' + str(self.warning_body))
        is_warning_head = check_repeat_percentage(self.warning_head, 1)
        # print('head:' + str(self.warning_head))

        if is_warning_leg:
            self.resultLable.setText(self.resultLable.text() + leg_content)

        if is_warning_body:
            self.resultLable.setText(self.resultLable.text() + body_content)

        if is_warning_head:
            self.resultLable.setText(self.resultLable.text() + head_content)

        if not is_warning_body and not is_warning_leg and not is_warning_head:
            self.resultLable.setText(self.resultLable.text() + "状态很好，继续保持！<br>")

    # 选取文件
    def open_file(self):
        self.file_path = QFileDialog.getOpenFileName(self, '选择一个视频', "./data", '*.mp4 *.mov')
        if self.file_path[0]:
            self.warning_leg = []
            self.warning_body = []
            self.warning_head = []
            self.file_path = self.file_path[0]
            self.cap = cv2.VideoCapture(self.file_path)
            self.timer.start()
            self.setup_video_writer(self.output_path)

    def setup_video_writer(self, output_path):
        # 获取帧率和帧大小
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # 创建视频写入器
        fourcc = cv2.VideoWriter.fourcc(*'mp4v')
        self.video_writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height), isColor=True)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VideoShow()
    desktopCenter = QDesktopWidget().availableGeometry().center()

    # 窗口在屏幕中央显示
    window.setGeometry(desktopCenter.x() - window.width() // 2,
                       desktopCenter.y() - window.height() // 2,
                       window.width(), window.height())
    window.show()

    sys.exit(app.exec_())

    try:
        main()
    except Exception as e:
        print(f"程序崩溃: {str(e)}")
        print("详细错误信息:")
        traceback.print_exc()
        # 添加暂停以便查看错误
        input("按Enter键退出...")
        sys.exit(1)