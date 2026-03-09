from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import uuid
from werkzeug.utils import secure_filename
from pose_analysis import analyze_running_posture
import logging
import traceback
import time
import datetime
import requests
from openai import OpenAI 

# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 允许所有来源访问所有路由
CORS(app, resources={r"/api/*": {"origins": "*"}})

# 讯飞星火API配置
XF_API_KEY = "sk-BE2MkrX7UrYwEblcAdD703A3709d457a83Fa9bC69c11CbCa"
XF_API_BASE = "https://maas-api.cn-huabei-1.xf-yun.com/v1" 
XF_MODEL_ID = "xop3qwen1b7"  

# 天气API配置 - 使用和风天气API
WEATHER_API_KEY = "c7d1c6783dcb434082f77ea5bdcd46b1" 
WEATHER_API_BASE = "https://devapi.qweather.com/v7"

# 创建OpenAI客户端
xf_client = OpenAI(
    api_key=XF_API_KEY,
    base_url=XF_API_BASE
)

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = '*'
    response.headers.add('Access-Control-Allow-Methods', '*')
    return response

# 配置
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB限制
ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi'}

# 确保上传目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# 添加中间件处理OPTIONS请求
@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = jsonify()
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Headers", "*")
        response.headers.add("Access-Control-Allow-Methods", "*")
        return response

# 在 Flask 后端添加处理 ngrok 警告的中间件
@app.before_request
def handle_ngrok_warning():
    # 检查是否有跳过警告的请求头
    if request.headers.get('ngrok-skip-browser-warning') == 'true':
        # 跳过 ngrok 警告的处理
        pass

# 添加根路由
@app.route('/')
def index():
    return "跑步姿态分析API服务已运行！请使用 /api/analyze 端点上传视频进行分析。"

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/analyze', methods=['POST', 'OPTIONS'])
def analyze_video():
    if request.method == 'OPTIONS':
        # 处理预检请求
        response = jsonify()
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Headers", "*")
        response.headers.add("Access-Control-Allow-Methods", "*")
        return response
    
    logger.info("收到分析请求")
    logger.info(f"请求头: {dict(request.headers)}")
    logger.info(f"请求文件: {request.files}")
    
    # 检查是否有文件上传
    if 'video' not in request.files:
        logger.warning("没有找到视频文件")
        return jsonify({'error': '没有上传视频文件'}), 400
    
    file = request.files['video']
    logger.info(f"收到文件: {file.filename}")
    
    # 检查文件名
    if file.filename == '':
        logger.warning("文件名为空")
        return jsonify({'error': '没有选择文件'}), 400
    
    # 检查文件类型
    if not allowed_file(file.filename):
        logger.warning(f"不支持的文件类型: {file.filename}")
        return jsonify({'error': '不支持的文件类型'}), 400
    
    # 生成唯一文件名
    filename = str(uuid.uuid4()) + '_' + secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    try:
        file.save(filepath)
        logger.info(f"文件已保存到: {filepath}")
        
        # 分析视频
        result = analyze_running_posture(filepath)
        logger.info("分析完成")
        
        # 返回分析结果
        response = jsonify({
            'success': True,
            'data': result
        })
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response
    except Exception as e:
        logger.error(f"分析过程中出错: {str(e)}")
        traceback.print_exc()
        response = jsonify({'error': f'分析失败: {str(e)}'})
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response, 500
    finally:
        # 清理上传的文件
        if os.path.exists(filepath):
            os.remove(filepath)
            logger.info(f"已清理文件: {filepath}")

@app.route('/api/health', methods=['GET', 'OPTIONS'])
def health_check():
    if request.method == 'OPTIONS':
        # 处理预检请求
        response = jsonify()
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Headers", "*")
        response.headers.add("Access-Control-Allow-Methods", "*")
        return response
    
    logger.info("收到健康检查请求")
    response = jsonify({'status': 'ok'})
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response

# AI API状态检查端点
@app.route('/api/ai-status', methods=['GET'])
def ai_status():
    """检查AI API连接状态"""
    try:
        # 测试连接
        test_messages = [{"role": "user", "content": "你好"}]
        response = xf_client.chat.completions.create(
            model=XF_MODEL_ID,
            messages=test_messages,
            temperature=0.7,
            max_tokens=10
        )
        
        return jsonify({
            "status": "success",
            "model": XF_MODEL_ID,
            "response": response.choices[0].message.content
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

# 网络连接测试端点
@app.route('/api/network-test', methods=['GET'])
def network_test():
    """测试网络连接"""
    try:
        # 测试连接到讯飞星火API
        response = requests.get(XF_API_BASE, timeout=5)
        return jsonify({
            'status': 'success',
            'api_connection': response.status_code == 200,
            'status_code': response.status_code
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# ==================== 天气API端点 ====================

@app.route('/api/weather', methods=['GET', 'OPTIONS'])
def get_weather():
    """获取天气信息API端点"""
    if request.method == 'OPTIONS':
        response = jsonify()
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Headers", "*")
        response.headers.add("Access-Control-Allow-Methods", "*")
        return response
    
    try:
        logger.info("=== 收到天气查询请求 ===")
        
        # 获取位置参数
        location = request.args.get('location', '北京')
        logger.info(f"查询位置: {location}")
        
        # 调用天气API
        weather_data = get_weather_data(location)
        
        if weather_data:
            return jsonify({
                'success': True,
                'weather': weather_data,
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
        else:
            return jsonify({'error': '获取天气信息失败'}), 500
            
    except Exception as e:
        logger.error(f"天气查询处理出错: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': f'天气查询失败: {str(e)}'}), 500

def get_weather_data(location):
    """获取天气数据 - 使用和风天气API"""
    try:
        # 第一步：获取位置ID
        geo_url = f"{WEATHER_API_BASE}/geo/city/lookup"
        geo_params = {
            'key': WEATHER_API_KEY,
            'location': location,
            'range': 'cn'
        }
        
        geo_response = requests.get(geo_url, params=geo_params, timeout=10)
        if geo_response.status_code != 200:
            logger.warning("无法获取位置信息，使用默认天气数据")
            return get_default_weather_data()
        
        geo_data = geo_response.json()
        if geo_data['code'] != '200' or not geo_data.get('location'):
            logger.warning("位置信息获取失败，使用默认天气数据")
            return get_default_weather_data()
        
        location_id = geo_data['location'][0]['id']
        city_name = geo_data['location'][0]['name']
        
        # 第二步：获取实时天气
        weather_url = f"{WEATHER_API_BASE}/weather/now"
        weather_params = {
            'key': WEATHER_API_KEY,
            'location': location_id
        }
        
        weather_response = requests.get(weather_url, params=weather_params, timeout=10)
        if weather_response.status_code != 200:
            logger.warning("无法获取实时天气，使用默认天气数据")
            return get_default_weather_data()
        
        weather_data = weather_response.json()
        if weather_data['code'] != '200':
            logger.warning("实时天气获取失败，使用默认天气数据")
            return get_default_weather_data()
        
        # 第三步：获取空气质量（可选）
        air_url = f"{WEATHER_API_BASE}/air/now"
        air_params = {
            'key': WEATHER_API_KEY,
            'location': location_id
        }
        
        air_quality = "未知"
        try:
            air_response = requests.get(air_url, params=air_params, timeout=5)
            if air_response.status_code == 200:
                air_data = air_response.json()
                if air_data['code'] == '200' and air_data.get('now'):
                    air_quality = air_data['now']['category']
        except Exception as e:
            logger.warning(f"空气质量获取失败: {str(e)}")
        
        # 解析天气数据
        now_data = weather_data['now']
        weather_info = {
            'location': city_name,
            'temperature': now_data['temp'],
            'condition': now_data['text'],
            'humidity': now_data['humidity'],
            'windSpeed': now_data['windScale'],
            'windDirection': now_data['windDir'],
            'pressure': now_data.get('pressure', '未知'),
            'visibility': now_data.get('vis', '未知'),
            'airQuality': air_quality,
            'updateTime': weather_data['updateTime']
        }
        
        logger.info(f"获取到天气数据: {weather_info}")
        return weather_info
        
    except Exception as e:
        logger.error(f"天气API调用失败: {str(e)}")
        return get_default_weather_data()

def get_default_weather_data():
    """获取默认天气数据（当API不可用时）"""
    return {
        'location': '当前位置',
        'temperature': '13',
        'condition': '晴朗',
        'humidity': '75',
        'windSpeed': '2',
        'windDirection': '东风',
        'pressure': '1025',
        'visibility': '18',
        'airQuality': '良',
        'updateTime': datetime.datetime.now().strftime('%Y-%m-%dT%H:%M+08:00'),
        'note': '默认数据'
    }

# ==================== 跑步建议功能 ====================

class RunningAdvisor:
    def __init__(self, xf_client, model_id):
        self.xf_client = xf_client
        self.model_id = model_id
    
    def get_running_suggestion(self, weather_data, user_stats, location):
        """生成跑步建议的主函数"""
        # 首先尝试使用AI生成建议
        try:
            return self._get_ai_suggestion(weather_data, user_stats, location)
        except Exception as e:
            logger.warning(f"AI建议生成失败，使用备用方案: {str(e)}")
            return self._get_fallback_suggestion(weather_data, user_stats, location)
    
    def _get_ai_suggestion(self, weather_data, user_stats, location):
        """使用AI生成跑步建议"""
        # 构建提示词
        prompt = self._build_suggestion_prompt(weather_data, user_stats, location)
        
        response = self.xf_client.chat.completions.create(
            model=self.model_id,
            messages=[
                {"role": "system", "content": """你是一名专业的跑步教练和健康顾问。请根据用户提供的天气、历史跑步数据和当前位置，给出专业、个性化、可执行的跑步建议。

请按照以下要求输出：
1. 使用自然流畅的中文段落，不要使用任何标记符号（如###、**、-等）
2. 不要使用编号列表或项目符号
3. 内容要连贯自然，像教练在面对面交流一样
4. 重点信息自然融入段落中，不要特别标注
5. 整体结构要像一段完整的文字建议，而不是分点列表
6. 语气要亲切专业，避免生硬的格式

请确保输出是纯文本，没有任何格式化标记。"""},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8, 
            max_tokens=500
        )
        
        return response.choices[0].message.content
    
    def _build_suggestion_prompt(self, weather_data, user_stats, location):
        """构建AI提示词"""
        prompt_parts = []
        
        # 天气信息
        if weather_data:
            prompt_parts.append("当前天气情况：")
            prompt_parts.append(f"温度{weather_data.get('temperature', '未知')}°C，{weather_data.get('condition', '未知')}，湿度{weather_data.get('humidity', '未知')}%，风速{weather_data.get('windSpeed', '未知')}级，空气质量{weather_data.get('airQuality', '未知')}。")
        
        # 用户数据
        if user_stats:
            prompt_parts.append(f"用户本周跑量{user_stats.get('weekly_distance', 0)}公里，本月跑量{user_stats.get('monthly_distance', 0)}公里，总共跑步{user_stats.get('total_runs', 0)}次，平均配速{user_stats.get('avg_pace', 0)}分钟/公里。")
            if user_stats.get('last_run_date'):
                prompt_parts.append(f"上次跑步时间是{user_stats.get('last_run_date')}。")
        
        # 当前时间季节
        current_time = datetime.datetime.now()
        season = self._get_season(current_time.month)
        prompt_parts.append(f"当前是{season}，时间{current_time.strftime('%H:%M')}。")
        
        prompt_parts.append("""
请基于以上信息，给我今天的个性化跑步建议。请用自然流畅的段落形式回答，包含以下内容但不限于：
- 适合的跑步时长和强度建议
- 基于天气的注意事项
- 装备建议
- 热身和拉伸建议
- 其他个性化建议

请用连贯的中文段落回答，不要使用任何标记符号，让建议读起来像教练的自然建议。""")
        
        return "\n".join(prompt_parts)
    
    def _get_season(self, month):
        """根据月份获取季节"""
        if month in [3, 4, 5]:
            return "春季"
        elif month in [6, 7, 8]:
            return "夏季"
        elif month in [9, 10, 11]:
            return "秋季"
        else:
            return "冬季"
    
    def _get_fallback_suggestion(self, weather_data, user_stats, location):
        """备用方案：基于规则生成自然语言建议"""
        suggestions = []
        
        # 基于天气的建议
        temp = int(weather_data.get('temperature', 20))
        condition = weather_data.get('condition', '晴朗')
        
        # 构建自然的建议段落
        if temp < 5:
            suggestions.append("今天气温比较低，建议您穿着保暖的运动服，热身时间要充足，至少15分钟以上。")
        elif temp < 10:
            suggestions.append("天气有点凉，建议穿着长袖运动服，热身时间不少于10分钟。")
        elif temp > 30:
            suggestions.append("今天天气比较热，建议选择早晚凉爽时段跑步，注意及时补水防止中暑。")
        elif temp > 25:
            suggestions.append("气温较高，建议携带饮用水，适当降低运动强度。")
        else:
            suggestions.append("今天天气温度适宜，非常适合进行跑步训练。")
        
        if '雨' in condition:
            suggestions.append("有降雨可能，建议室内运动或者携带防水装备，注意防滑。")
        elif '雪' in condition:
            suggestions.append("有降雪，建议选择室内运动确保安全。")
        elif '雾' in condition:
            suggestions.append("有雾霾，建议佩戴口罩或选择室内运动保护呼吸道。")
        elif '大风' in condition:
            suggestions.append("风比较大，建议选择背风路线跑步，注意防风。")
        
        # 基于用户数据的建议
        weekly_distance = float(user_stats.get('weekly_distance', 0))
        total_runs = user_stats.get('total_runs', 0)
        
        if total_runs == 0:
            suggestions.append("作为新手跑者，建议从3-5公里开始，循序渐进增加距离，不要急于求成。")
        elif weekly_distance < 10:
            suggestions.append("本周跑量相对较少，可以适当增加训练频率，保持运动习惯。")
        elif weekly_distance > 30:
            suggestions.append("本周跑量较大，要注意合理安排休息，给身体足够的恢复时间。")
        
        # 基于时间的建议
        current_hour = datetime.datetime.now().hour
        if 5 <= current_hour <= 8:
            suggestions.append("早晨空气清新，是跑步的好时机，但要注意充分热身唤醒身体。")
        elif current_hour >= 20:
            suggestions.append("夜间跑步请选择光线良好的安全路线，穿着反光装备确保安全。")
        
        # 将建议组合成自然段落
        if suggestions:
            # 将列表转换为连贯的段落
            suggestion_text = " ".join(suggestions)
            
            # 添加开头和结尾使其更自然
            final_suggestion = f"根据您的情况，{suggestion_text}建议您根据自己的体感适当调整，享受跑步的乐趣。"
            return final_suggestion
        else:
            return "今天天气条件不错，建议进行适度的跑步训练。根据自身感觉调整强度，保持规律的运动习惯对健康很有益处。"

# 创建跑步建议器实例
running_advisor = RunningAdvisor(xf_client, XF_MODEL_ID)

@app.route('/api/running-suggestion', methods=['POST', 'OPTIONS'])
def running_suggestion():
    """跑步建议API端点"""
    if request.method == 'OPTIONS':
        # 处理预检请求
        response = jsonify()
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Headers", "*")
        response.headers.add("Access-Control-Allow-Methods", "*")
        return response
    
    try:
        logger.info("=== 收到跑步建议请求 ===")
        
        # 检查请求数据
        data = request.get_json()
        if not data:
            logger.warning("缺少请求数据")
            return jsonify({'error': '缺少请求数据'}), 400
        
        weather_data = data.get('weather', {})
        user_stats = data.get('user_stats', {})
        location = data.get('location', {})
        
        logger.info(f"天气数据: {weather_data}")
        logger.info(f"用户数据: {user_stats}")
        logger.info(f"位置数据: {location}")
        
        # 生成跑步建议
        suggestion = running_advisor.get_running_suggestion(weather_data, user_stats, location)
        
        logger.info(f"生成的建议: {suggestion}")
        
        return jsonify({
            'success': True,
            'suggestion': suggestion,
            'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        
    except Exception as e:
        logger.error(f"跑步建议处理出错: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'生成跑步建议时出错: {str(e)}'
        }), 500

# ==================== 健康咨询端点 ====================

@app.route('/api/health-consult', methods=['POST', 'OPTIONS'])
def health_consult():
    if request.method == 'OPTIONS':
        # 处理预检请求
        response = jsonify()
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Headers", "*")
        response.headers.add("Access-Control-Allow-Methods", "*")
        return response
    
    try:
        logger.info("=== 收到健康咨询请求 ===")
        
        # 检查请求数据
        data = request.get_json()
        if not data:
            logger.warning("缺少请求数据")
            return jsonify({'error': '缺少请求数据'}), 400
        
        user_message = data.get('message', '')
        if not user_message:
            logger.warning("用户消息为空")
            return jsonify({'error': '请输入咨询内容'}), 400
        
        # 使用讯飞星火API
        try:
            response = xf_client.chat.completions.create(
                model=XF_MODEL_ID,
                messages=[
                    {"role": "system", "content": """你是一名专业的跑步健康顾问，专注于跑步相关的健康咨询。请用自然流畅的中文进行回答，不要使用任何标记符号（如###、**、-等），不要使用编号列表。

回答要求：
1. 使用连贯的段落形式，像朋友间自然交流一样
2. 重要信息自然融入文本中，不要特别标注
3. 语气亲切专业，避免生硬的格式
4. 内容要实用具体，便于理解执行
5. 确保回答是纯文本，没有任何格式化标记"""},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7,
                max_tokens=300
            )
            
            ai_response = response.choices[0].message.content
            
            return jsonify({
                'success': True,
                'response': ai_response
            })
        except Exception as e:
            logger.error(f"讯飞星火API调用失败: {str(e)}")
            # 提供备用响应
            return jsonify({
                'success': True,
                'response': get_fallback_response(user_message),
                'note': 'AI服务暂时不可用，这是备用响应'
            })
            
    except Exception as e:
        logger.error(f"健康咨询处理出错: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'success': True,
            'response': get_fallback_response(""),
            'note': '服务器内部错误，使用备用响应'
        })

def get_fallback_response(user_message):
    """当AI服务不可用时提供自然的备用响应"""
    fallback_responses = {
        "膝盖": "跑步后膝盖疼痛可能是由于跑步姿势不正确、跑鞋不合适或训练强度过大等原因。建议先检查跑步姿势是否正确，选择合适的跑鞋，适当减少训练强度，同时进行一些膝盖强化训练来改善情况。如果疼痛持续，建议咨询专业医生。",
        "呼吸": "跑步时的呼吸很重要，应该采用深而有节奏的呼吸方式。一般建议每2到4步完成一次呼吸循环，根据跑步强度来调整呼吸频率。保持呼吸平稳有助于提高跑步效率和舒适度，让跑步过程更加轻松愉快。",
        "姿势": "良好的跑步姿势对身体很重要，包括身体略微前倾，眼睛平视前方，肩膀放松，手臂自然摆动，膝盖微屈，脚掌中部着地。保持核心稳定，避免过度摆动，这样既能提高效率又能减少受伤风险。",
        "冷": "天气冷的时候跑步需要特别注意保暖和热身。建议穿着合适的保暖运动服装，充分热身让身体暖和起来，可以选择中午气温较高的时候跑步，或者考虑室内运动来替代户外跑步。",
        "不想跑": "运动积极性有时会波动是很正常的现象。可以尝试设定一些小目标，找到跑步伙伴互相鼓励，或者尝试不同的运动方式来保持新鲜感。重要的是找到让自己感到快乐的运动方式。",
        "你是谁": "我是您的跑步健康顾问，专注于跑步相关的健康咨询。我可以帮助您解答跑步姿势、训练方法、伤病预防等方面的问题，为您提供专业的建议和指导。",
        "怎么只回答一个问题": "抱歉给您带来了不好的体验！我会根据您的具体问题提供详细个性化的建议。请告诉我您关心的具体跑步健康问题，我会用心为您解答，帮助您更好地享受跑步的乐趣。"
    }
    
    # 简单的关键词匹配
    for keyword, response in fallback_responses.items():
        if keyword in user_message:
            return response
    
    # 默认响应 - 改为更自然的段落
    return "您好！关于跑步健康的问题，我建议您注意保持正确的跑步姿势，选择合适的跑鞋，循序渐进地增加训练强度，同时不要忽视热身和拉伸的重要性。如果您有具体的问题或困惑，欢迎详细描述，我会根据您的情况给出专业建议。"

# 服务状态监控端点
@app.route('/api/status', methods=['GET'])
def service_status():
    status = {
        'service': 'running',
        'timestamp': datetime.datetime.now().isoformat(),
        'version': '1.0.0'
    }
    
    try:
        # 测试讯飞星火API连接
        test_messages = [{"role": "user", "content": "你好"}]
        response = xf_client.chat.completions.create(
            model=XF_MODEL_ID,
            messages=test_messages,
            temperature=0.7,
            max_tokens=10
        )
        status['ai_api_connection'] = 'available'
    except Exception as e:
        status['ai_api_connection'] = f'error_{str(e)}'
    
    return jsonify(status)

if __name__ == '__main__':
    # 启动前检查API密钥
    if not XF_API_KEY or XF_API_KEY == "<YOUR_API_KEY>":
        logger.warning("警告: 未配置有效的讯飞星火API密钥")
        logger.warning("AI健康咨询功能可能无法正常工作")
    
    if not WEATHER_API_KEY or WEATHER_API_KEY == "your_weather_api_key":
        logger.warning("警告: 未配置有效的天气API密钥")
        logger.warning("天气查询功能将使用默认数据")
    
    # 添加详细日志配置
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s %(levelname)s %(message)s',
        handlers=[
            logging.FileHandler("app.log"),
            logging.StreamHandler()
        ]
    )
    
    # 列出所有已注册路由
    logger.info("已注册路由:")
    for rule in app.url_map.iter_rules():
        logger.info(f" - {rule}")
    
    app.run(host='0.0.0.0', port=5000, debug=True)