import cv2
import mediapipe as mp
import numpy as np

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

# 判断数组中某一数字重复是否超过30%
def check_repeat_percentage(numbers, target):
    if not numbers:
        return False
    count = numbers.count(target)
    total_count = len(numbers)
    repeat_percentage = (count / total_count) * 100
    return repeat_percentage >= 30

# 分析跑步姿态的主要函数
def analyze_running_posture(video_path):
    # 初始化变量
    warning_leg = []
    warning_body = []
    warning_head = []
    
    # 初始化MediaPipe Pose
    mp_pose = mp.solutions.pose
    pose = mp_pose.Pose(
        static_image_mode=False,
        model_complexity=2,
        smooth_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.8
    )
    
    # 打开视频文件
    cap = cv2.VideoCapture(video_path)
    frame_count = 0
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
            
        # 转换为RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # 处理帧
        results = pose.process(rgb_frame)
        
        if results.pose_landmarks:
            h, w = frame.shape[0], frame.shape[1]
            
            # 提取关键点坐标
            landmarks = results.pose_landmarks.landmark
            
            # 计算腿部角度
            right_hip = landmarks[24]
            right_knee = landmarks[26]
            right_ankle = landmarks[28]
            left_hip = landmarks[23]
            left_knee = landmarks[25]
            left_ankle = landmarks[27]
            
            # 计算右腿角度
            p1 = (x_restore(right_hip.x, w), y_restore(right_hip.y, h))
            p2 = (x_restore(right_knee.x, w), y_restore(right_knee.y, h))
            p3 = (x_restore(right_ankle.x, w), y_restore(right_ankle.y, h))
            v1 = (p1[0] - p2[0], p1[1] - p2[1])
            v2 = (p3[0] - p2[0], p3[1] - p2[1])
            angle_leg = calculate_angle(v1, v2)
            
            if angle_leg > 165:
                warning_leg.append(1)
            else:
                warning_leg.append(0)
                
            # 计算身体角度
            right_shoulder = landmarks[12]
            left_shoulder = landmarks[11]
            right_ear = landmarks[8]
            
            p1 = (x_restore((right_shoulder.x + left_shoulder.x)/2, w), 
                  y_restore((right_shoulder.y + left_shoulder.y)/2, h))
            p2 = (x_restore(right_hip.x, w), y_restore(right_hip.y, h))
            p3 = (x_restore(right_hip.x, w), y_restore(right_shoulder.y, h))
            
            v1 = (p1[0] - p2[0], p1[1] - p2[1])
            v2 = (p3[0] - p2[0], p3[1] - p2[1])
            angle_body = calculate_angle(v1, v2)
            
            if angle_body > 10:
                warning_body.append(1)
            else:
                warning_body.append(0)
                
            # 计算头部角度
            p4 = (x_restore(right_ear.x, w), y_restore(right_ear.y, h))
            v3 = (p4[0] - p2[0], p4[1] - p2[1])
            angle_head = calculate_angle(v2, v3)
            
            if angle_head > 10:
                warning_head.append(1)
            else:
                warning_head.append(0)
                
        frame_count += 1
        if frame_count > 100:  # 限制分析帧数，避免处理时间过长
            break
            
    cap.release()
    
    # 分析结果
    is_warning_leg = check_repeat_percentage(warning_leg, 1)
    is_warning_body = check_repeat_percentage(warning_body, 1)
    is_warning_head = check_repeat_percentage(warning_head, 1)
    
    # 生成分析报告
    details = ""
    if is_warning_leg:
        details += "脚部着地点与身体重心相差太远，会造成刹车效应，进而导致膝盖和脚踝受伤；应尽量提升膝盖，抬起大腿或提高步频。<br>"
    if is_warning_body:
        details += "身体弯腰驼背，过度前倾，会导致腰肌劳损；应挺直身体并略微前倾，打开肩部，挺胸抬头。<br>"
    if is_warning_head:
        details += "头部俯仰角度过大，会导致颈肩部肌肉紧张; 应视线水平目视前方，自然挺胸抬头。<br>"
    
    is_good = not (is_warning_leg or is_warning_body or is_warning_head)
    
    if is_good:
        details = "状态很好，继续保持！"
    
    return {
        'is_good': is_good,
        'details': details,
        'warnings': {
            'leg': is_warning_leg,
            'body': is_warning_body,
            'head': is_warning_head
        }
    }