// miniprogram/pages/index/index.js
const app = getApp()

Page({
  data: {
    videoSrc: '',
    isLoading: false,
    analysisResult: null,
    processedVideoUrl: '',
    chatMessages: [],
    chatInput: '',
    isSending: false,
    currentTab: 0, // 0:姿态分析, 1:跑步记录, 2:AI健康咨询
    isRunning: false,
    isPaused: false,
    showMap: true,
    scrollHeight: 500,
    chatScrollHeight: 400,
    currentLocation: {
      latitude: 39.9042,
      longitude: 116.4074
    },
    runningData: {
      distance: 0,
      duration: '00:00',
      pace: '0',
      cadence: 0,
      calories: 0,
      steps: 0,
      avgPace: 0,
      avgCadence: 0
    },
    pathPoints: [],
    pathPolyline: [{
      points: [],
      color: '#007AFF',
      width: 4,
      dottedLine: false
    }],
    runningHistory: [],
    startTime: 0,
    timer: null,
    totalSeconds: 0,
    stepCount: 0,
    lastStepTime: 0,
    runningSuggestion: '',
    isLoadingSuggestion: false,
    weatherData: null,
    userStats: null,
    isLoadingWeather: false,
    runningSuitability: {
      score: 0,
      text: '加载中...'
    },
    scrollToView: 'last-message',
    weeklyStats: {
      totalDistance: '0.0',
      runCount: '0',
      avgPace: '0',
      lastRunDate: '',
      lastRunDistance: '0',
      lastRunDuration: '00:00',
      lastRunPace: '0'
    },
    isSpeaking: false,
    speechText: '',
    voiceSettings: {
      rate: 1.0,
      pitch: 1.0,
      volume: 1.0,
      show: false
    },
    speechSynthesis: null,
    currentUtterance: null
  },

  // 页面加载时执行
  onLoad: function(options) {
    console.log('页面加载开始');
    this.testBackendConnection();
    this.loadRunningHistory();
    this.initLocation();
    this.getWeatherInfo();
    this.getRunningSuggestion();
  
    var that = this;
    setTimeout(function() {
      that.calculateScrollHeight();
      that.calculateWeeklyStats();
      console.log('页面加载完成，当前标签页:', that.data.currentTab);
    }, 100);
  },


  // 计算滚动区域高度
  calculateScrollHeight: function() {
    var that = this;
    
    try {
      // 使用微信小程序的API获取系统信息
      wx.getSystemInfo({
        success: function(res) {
          var windowHeight = res.windowHeight;
          console.log('窗口高度:', windowHeight);
          
          // 创建选择器查询
          var query = wx.createSelectorQuery();
          query.select('.header').boundingClientRect();
          query.select('.tab-container').boundingClientRect();
          query.exec(function(rects) {
            var headerHeight = rects[0] ? rects[0].height : 0;
            var tabHeight = rects[1] ? rects[1].height : 0;
            
            var scrollHeight = windowHeight - headerHeight - tabHeight - 20;
            
            that.setData({
              scrollHeight: Math.max(scrollHeight, 400),
              chatScrollHeight: scrollHeight - 120
            });
            
            console.log('计算后的滚动高度:', scrollHeight);
          });
        }
      });
    } catch (error) {
      console.error('计算高度时出错:', error);
      // 备用方案
      that.setData({
        scrollHeight: 500,
        chatScrollHeight: 400
      });
    }
  },

  // 新增方法：计算周统计数据
  calculateWeeklyStats: function() {
    var history = this.data.runningHistory || [];
    var now = new Date();
    var oneWeekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
    
    // 筛选本周的跑步记录
    var weeklyRuns = history.filter(function(run) {
      var runDate = new Date(run.date);
      return runDate >= oneWeekAgo;
    });
    
    // 计算周跑量
    var totalDistance = weeklyRuns.reduce(function(sum, run) {
      return sum + (run.distance || 0);
    }, 0);
    
    // 计算平均配速
    var avgPace = weeklyRuns.length > 0 ? 
      weeklyRuns.reduce(function(sum, run) {
        return sum + parseFloat(run.avgPace || 0);
      }, 0) / weeklyRuns.length : 0;
    
    // 获取最近一次跑步数据
    var lastRun = history.length > 0 ? history[0] : null;
    
    var weeklyStats = {
      totalDistance: totalDistance.toFixed(1),
      runCount: weeklyRuns.length.toString(),
      avgPace: avgPace.toFixed(1),
      lastRunDate: lastRun ? this.formatShortDate(new Date(lastRun.date)) : '',
      lastRunDistance: lastRun ? (lastRun.distance || 0).toFixed(1) : '0',
      lastRunDuration: lastRun ? (lastRun.duration || '00:00') : '00:00',
      lastRunPace: lastRun ? (lastRun.avgPace || '0') : '0'
    };
    
    this.setData({
      weeklyStats: weeklyStats
    });
    
    console.log('周统计数据计算完成:', weeklyStats);
  },

  // 新增方法：格式化短日期
  formatShortDate: function(date) {
    var month = (date.getMonth() + 1).toString().padStart(2, '0');
    var day = date.getDate().toString().padStart(2, '0');
    var hours = date.getHours().toString().padStart(2, '0');
    var minutes = date.getMinutes().toString().padStart(2, '0');
    return month + '-' + day + ' ' + hours + ':' + minutes;
  },

  // 新增方法：从仪表盘开始跑步
  startRunningFromDashboard: function() {
    if (this.data.isRunning) {
      this.setData({ currentTab: 1 });
      return;
    }
    
    var that = this;
    wx.authorize({
      scope: 'scope.userLocation',
      success: function() {
        that.startRunningProcess();
        setTimeout(function() {
          that.setData({ currentTab: 1 });
        }, 500);
      },
      fail: function() {
        wx.showModal({
          title: '需要位置权限',
          content: '请授权位置权限以记录跑步轨迹',
          success: function(res) {
            if (res.confirm) wx.openSetting();
          }
        });
      }
    });
  },

  // 切换标签页
  switchTab: function(e) {
    var tab = parseInt(e.currentTarget.dataset.tab);
    var that = this;
    
    console.log('切换到标签页:', tab);
    
    this.setData({ currentTab: tab }, function() {
      setTimeout(function() {
        that.calculateScrollHeight();
      }, 50);
      
      if (tab === 2 && that.data.chatMessages.length === 0) {
        that.addWelcomeMessage();
      }
    });
    
    if (tab === 1) {
      this.initLocation();
    }
  },

  // 添加欢迎消息
  addWelcomeMessage: function() {
    var welcomeMessage = {
      role: 'assistant',
      content: '您好！我是跑步健康顾问，有什么关于跑步健康的问题可以问我。'
    };
    
    this.setData({
      chatMessages: [welcomeMessage]
    });
  },

  // 快速提问功能
  askQuickQuestion: function(e) {
    var question = e.currentTarget.dataset.question;
    this.sendChatMessageDirectly(question);
  },

  // 直接发送消息（用于快速提问）
  sendChatMessageDirectly: function(message) {
    if (!message.trim()) return;
    
    var userMessage = {
      role: 'user',
      content: message
    };
    
    var newMessages = this.data.chatMessages.concat([userMessage]);
    this.setData({
      chatMessages: newMessages,
      isSending: true
    });
    
    this.scrollToBottom();
    this.sendToBackend(message);
  },

  // 处理聊天输入
  onChatInput: function(e) {
    this.setData({
      chatInput: e.detail.value
    });
  },

  // 发送聊天消息
  sendChatMessage: function() {
    var message = this.data.chatInput.trim();
    if (!message) {
      wx.showToast({
        title: '请输入消息',
        icon: 'none'
      });
      return;
    }
    
    var userMessage = {
      role: 'user',
      content: message
    };
    
    var newMessages = this.data.chatMessages.concat([userMessage]);
    this.setData({
      chatMessages: newMessages,
      chatInput: '',
      isSending: true
    });
    
    this.scrollToBottom();
    this.sendToBackend(message);
  },

  // 发送到后端API
  sendToBackend: function(message) {
    var that = this;
    
    wx.request({
      url: app.globalData.apiBase + '/api/health-consult',
      method: 'POST',
      header: {
        'Content-Type': 'application/json',
        'ngrok-skip-browser-warning': 'true'
      },
      data: {
        message: message
      },
      success: function(res) {
        if (res.statusCode === 200 && res.data && res.data.success) {
          var aiMessage = {
            role: 'assistant',
            content: res.data.response || '收到您的咨询，我会尽快为您解答。'
          };
          
          var updatedMessages = that.data.chatMessages.concat([aiMessage]);
          that.setData({
            chatMessages: updatedMessages,
            isSending: false
          });
          
          setTimeout(function() {
            that.scrollToBottom();
          }, 100);
        } else {
          that.handleApiError(res.data ? res.data.error : 'API返回错误');
        }
      },
      fail: function(err) {
        that.handleNetworkError();
      }
    });
  },

  // 处理API错误
  handleApiError: function(error) {
    var errorMessage = {
      role: 'assistant',
      content: '抱歉，服务暂时不可用。请稍后重试。'
    };
    
    var errorMessages = this.data.chatMessages.concat([errorMessage]);
    this.setData({
      chatMessages: errorMessages,
      isSending: false
    });
    
    wx.showToast({
      title: '咨询失败',
      icon: 'none'
    });
    
    this.scrollToBottom();
  },

  // 处理网络错误
  handleNetworkError: function() {
    var errorMessage = {
      role: 'assistant',
      content: '网络连接失败，请检查网络后重试。'
    };
    
    var errorMessages = this.data.chatMessages.concat([errorMessage]);
    this.setData({
      chatMessages: errorMessages,
      isSending: false
    });
    
    wx.showToast({
      title: '网络错误',
      icon: 'none'
    });
    
    this.scrollToBottom();
  },

  // 滚动到底部
  scrollToBottom: function() {
    var that = this;
    this.setData({
      scrollToView: 'last-message'
    });
    
    setTimeout(function() {
      that.setData({
        scrollToView: 'last-message'
      });
    }, 100);
  },

  // 获取跑步建议
  getRunningSuggestion: function() {
    var that = this;
    
    if (this.data.runningSuggestion && !this.data.isLoadingSuggestion) {
      return;
    }
    
    this.setData({ isLoadingSuggestion: true });
    
    var userStats = this.calculateUserStats();
    
    this.getWeatherData()
      .then(function(weatherData) {
        return that.callAISuggestionAPI(weatherData, userStats);
      })
      .then(function(suggestion) {
        that.setData({
          runningSuggestion: suggestion,
          isLoadingSuggestion: false
        });
      })
      .catch(function(err) {
        console.error('获取跑步建议失败:', err);
        var fallbackSuggestion = that.generateFallbackSuggestion(userStats);
        that.setData({
          runningSuggestion: fallbackSuggestion,
          isLoadingSuggestion: false
        });
      });
  },

  // 计算用户统计数据
  calculateUserStats: function() {
    var history = this.data.runningHistory || [];
    var now = new Date();
    var oneWeekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
    var oneMonthAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
    
    var weeklyRuns = history.filter(function(run) {
      var runDate = new Date(run.date);
      return runDate >= oneWeekAgo;
    });
    
    var monthlyRuns = history.filter(function(run) {
      var runDate = new Date(run.date);
      return runDate >= oneMonthAgo;
    });
    
    var weeklyDistance = weeklyRuns.reduce(function(sum, run) { 
      return sum + (run.distance || 0); 
    }, 0);
    
    var monthlyDistance = monthlyRuns.reduce(function(sum, run) { 
      return sum + (run.distance || 0); 
    }, 0);
    
    var avgPace = history.length > 0 ? 
      history.reduce(function(sum, run) { 
        return sum + parseFloat(run.avgPace || 0); 
      }, 0) / history.length : 0;
    
    return {
      weekly_distance: weeklyDistance.toFixed(1),
      monthly_distance: monthlyDistance.toFixed(1),
      total_runs: history.length,
      avg_pace: avgPace.toFixed(1),
      last_run_date: history.length > 0 ? history[0].date : null
    };
  },

  
  // 获取天气信息 - 连接到后端API
  getWeatherInfo: function() {
    var that = this;
    
    this.setData({ isLoadingWeather: true });
    
    console.log('开始获取天气信息...');
    
    wx.request({
      url: app.globalData.apiBase + '/api/weather',
      method: 'GET',
      data: {
        location: '北京' // 可以根据用户位置动态设置
      },
      header: {
        'Content-Type': 'application/json',
        'ngrok-skip-browser-warning': 'true'
      },
      success: function(res) {
        console.log('天气API响应:', res);
        
        if (res.statusCode === 200 && res.data.success) {
          var weatherData = res.data.weather;
          var suitability = that.calculateRunningSuitability(weatherData);
          
          that.setData({
            weatherData: weatherData,
            runningSuitability: suitability,
            isLoadingWeather: false
          });
          
          console.log('天气数据获取成功:', weatherData);
        } else {
          console.error('获取天气信息失败:', res.data);
          that.useDefaultWeatherData();
        }
      },
      fail: function(err) {
        console.error('天气API请求失败:', err);
        that.useDefaultWeatherData();
      }
    });
  },

  // 使用默认天气数据
  useDefaultWeatherData: function() {
    var defaultWeather = {
      temperature: '20',
      condition: '晴朗',
      humidity: '60',
      windSpeed: '3',
      airQuality: '良',
      location: '北京'
    };
    var suitability = this.calculateRunningSuitability(defaultWeather);
    
    this.setData({
      weatherData: defaultWeather,
      runningSuitability: suitability,
      isLoadingWeather: false
    });
    
    console.log('使用默认天气数据');
  },

  // 获取跑步建议 - 连接到后端API
  getRunningSuggestion: function() {
    var that = this;
    
    if (this.data.runningSuggestion && !this.data.isLoadingSuggestion) {
      return;
    }
    
    this.setData({ isLoadingSuggestion: true });
    
    console.log('开始获取跑步建议...');
    
    // 准备请求数据
    var requestData = {
      weather: this.data.weatherData || {},
      user_stats: this.calculateUserStats(),
      location: {
        city: '北京',
        latitude: this.data.currentLocation.latitude,
        longitude: this.data.currentLocation.longitude
      }
    };
    
    console.log('跑步建议请求数据:', requestData);
    
    wx.request({
      url: app.globalData.apiBase + '/api/running-suggestion',
      method: 'POST',
      data: requestData,
      header: {
        'Content-Type': 'application/json',
        'ngrok-skip-browser-warning': 'true'
      },
      success: function(res) {
        console.log('跑步建议API响应:', res);
        
        if (res.statusCode === 200 && res.data.success) {
          that.setData({
            runningSuggestion: res.data.suggestion,
            isLoadingSuggestion: false
          });
          
          console.log('跑步建议获取成功:', res.data.suggestion);
        } else {
          console.error('获取跑步建议失败:', res.data);
          that.useFallbackSuggestion();
        }
      },
      fail: function(err) {
        console.error('跑步建议API请求失败:', err);
        that.useFallbackSuggestion();
      }
    });
  },

  // 使用备用建议
  useFallbackSuggestion: function() {
    var userStats = this.calculateUserStats();
    var fallbackSuggestion = this.generateFallbackSuggestion(userStats);
    
    this.setData({
      runningSuggestion: fallbackSuggestion,
      isLoadingSuggestion: false
    });
    
    console.log('使用备用跑步建议');
  },

  // 刷新跑步建议
  refreshSuggestion: function() {
    console.log('手动刷新跑步建议');
    this.setData({ 
      runningSuggestion: '',
      isLoadingSuggestion: true 
    });
    this.getRunningSuggestion();
  },

  // 刷新天气信息
  refreshWeather: function() {
    console.log('手动刷新天气信息');
    this.setData({ 
      weatherData: null,
      isLoadingWeather: true 
    });
    this.getWeatherInfo();
  },

  // 修改后的计算用户统计数据方法
  calculateUserStats: function() {
    var history = this.data.runningHistory || [];
    var now = new Date();
    var oneWeekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
    var oneMonthAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
    
    // 筛选本周的跑步记录
    var weeklyRuns = history.filter(function(run) {
      var runDate = new Date(run.date);
      return runDate >= oneWeekAgo;
    });
    
    // 筛选本月的跑步记录
    var monthlyRuns = history.filter(function(run) {
      var runDate = new Date(run.date);
      return runDate >= oneMonthAgo;
    });
    
    // 计算周跑量
    var weeklyDistance = weeklyRuns.reduce(function(sum, run) { 
      return sum + (parseFloat(run.distance) || 0); 
    }, 0);
    
    // 计算月跑量
    var monthlyDistance = monthlyRuns.reduce(function(sum, run) { 
      return sum + (parseFloat(run.distance) || 0); 
    }, 0);
    
    // 计算平均配速
    var totalPace = 0;
    var validRuns = 0;
    
    history.forEach(function(run) {
      var pace = parseFloat(run.avgPace);
      if (pace && pace > 0) {
        totalPace += pace;
        validRuns++;
      }
    });
    
    var avgPace = validRuns > 0 ? totalPace / validRuns : 0;
    
    // 获取最近一次跑步
    var lastRun = history.length > 0 ? history[0] : null;
    
    return {
      weekly_distance: weeklyDistance.toFixed(1),
      monthly_distance: monthlyDistance.toFixed(1),
      total_runs: history.length,
      avg_pace: avgPace.toFixed(1),
      last_run_date: lastRun ? lastRun.date : null,
      last_run_distance: lastRun ? (parseFloat(lastRun.distance) || 0).toFixed(1) : '0'
    };
  },

  // 修改后的计算跑步适宜度方法
  calculateRunningSuitability: function(weatherData) {
    if (!weatherData) return { score: 0, text: '未知' };
    
    var score = 0;
    var temp = parseInt(weatherData.temperature) || 20;
    var condition = weatherData.condition || '晴朗';
    var airQuality = weatherData.airQuality || '良';
    var humidity = parseInt(weatherData.humidity) || 60;
    
    // 温度评分 (0-40分)
    if (temp >= 15 && temp <= 25) score += 40;
    else if ((temp >= 10 && temp < 15) || (temp > 25 && temp <= 30)) score += 30;
    else if ((temp >= 5 && temp < 10) || (temp > 30 && temp <= 35)) score += 20;
    else score += 10;
    
    // 天气状况评分 (0-30分)
    if (condition.indexOf('晴') !== -1 || condition.indexOf('多云') !== -1) score += 30;
    else if (condition.indexOf('阴') !== -1) score += 25;
    else if (condition.indexOf('小雨') !== -1 || condition.indexOf('阵雨') !== -1) score += 15;
    else if (condition.indexOf('雨') !== -1 || condition.indexOf('雪') !== -1 || condition.indexOf('雾') !== -1) score += 5;
    else score += 20;
    
    // 空气质量评分 (0-20分)
    if (airQuality === '优') score += 20;
    else if (airQuality === '良') score += 15;
    else if (airQuality === '轻度污染') score += 10;
    else if (airQuality === '中度污染') score += 5;
    else if (airQuality === '重度污染') score += 0;
    
    // 湿度评分 (0-10分)
    if (humidity >= 40 && humidity <= 70) score += 10;
    else if ((humidity >= 30 && humidity < 40) || (humidity > 70 && humidity <= 80)) score += 5;
    
    // 转换为5星评分
    var starScore = Math.round((score / 100) * 5);
    starScore = Math.max(1, Math.min(5, starScore)); // 确保在1-5之间
    
    var suitabilityText = '';
    if (score >= 80) suitabilityText = '非常适宜';
    else if (score >= 60) suitabilityText = '适宜';
    else if (score >= 40) suitabilityText = '一般';
    else if (score >= 20) suitabilityText = '不适宜';
    else suitabilityText = '极不适宜';
    
    return { 
      score: starScore, 
      text: suitabilityText,
      originalScore: score // 保留原始分数用于调试
    };
  },

  // 获取天气图标
  getWeatherIcon: function(condition) {
    if (!condition) return 'info';
    
    var iconMap = {
      '晴': 'clear',
      '多云': 'partly-cloudy',
      '阴': 'cloudy',
      '雨': 'rain',
      '小雨': 'light-rain',
      '中雨': 'moderate-rain',
      '大雨': 'heavy-rain',
      '暴雨': 'storm',
      '雪': 'snow',
      '小雪': 'light-snow',
      '中雪': 'moderate-snow',
      '大雪': 'heavy-snow',
      '雾': 'fog',
      '雾霾': 'haze',
      '沙尘': 'dust'
    };
    
    for (var key in iconMap) {
      if (condition.indexOf(key) !== -1) {
        return iconMap[key];
      }
    }
    
    return 'info';
  },

  // 获取空气质量样式类
  getAirQualityClass: function(airQuality) {
    if (!airQuality) return '';
    
    var classMap = {
      '优': 'excellent',
      '良': 'good',
      '轻度污染': 'light-pollution',
      '中度污染': 'moderate-pollution',
      '重度污染': 'heavy-pollution'
    };
    
    return classMap[airQuality] || '';
  },

  // 获取适宜度样式类
  getSuitabilityClass: function(score) {
    if (score >= 4) return 'excellent';
    if (score >= 3) return 'good';
    if (score >= 2) return 'fair';
    if (score >= 1) return 'poor';
    return 'bad';
  },

  // 测试后端连接
  testBackendConnection: function() {
    var that = this;
    
    wx.request({
      url: app.globalData.apiBase + '/api/health',
      method: 'GET',
      header: {
        'Content-Type': 'application/json',
        'ngrok-skip-browser-warning': 'true'
      },
      success: function(res) {
        if (res.statusCode === 200) {
          console.log('后端连接测试成功:', res.data);
        } else {
          console.error('后端连接测试失败，状态码:', res.statusCode);
        }
      },
      fail: function(err) {  
        console.error('后端连接测试失败:', err);
      }
    });
  },

  // 保存跑步记录后刷新建议
  saveRunningRecord: function() {
    var record = {
      id: Date.now(),
      date: this.formatDate(new Date()),
      distance: this.data.runningData.distance,
      duration: this.data.runningData.duration,
      avgPace: this.data.runningData.avgPace,
      avgCadence: this.data.runningData.avgCadence,
      calories: this.data.runningData.calories,
      steps: this.data.runningData.steps,
      path: this.data.pathPoints
    };

    var history = [record].concat(this.data.runningHistory);
    this.setData({ runningHistory: history.slice(0, 10) });
    wx.setStorageSync('runningHistory', history.slice(0, 10));
    
    this.calculateWeeklyStats();
    
    // 保存记录后刷新跑步建议
    var that = this;
    setTimeout(function() {
      that.refreshSuggestion();
    }, 1000);
  },

  // 修改后的生成备用建议方法
  generateFallbackSuggestion: function(userStats) {
    var now = new Date();
    var hour = now.getHours();
    var weather = this.data.weatherData || { temperature: 18, condition: '晴朗' };
    var temp = parseInt(weather.temperature) || 20;
    var suggestion = '';
    
    // 基于时间的建议
    if (hour >= 5 && hour <= 10) {
      suggestion += '早晨空气清新，是跑步的好时机。';
    } else if (hour > 10 && hour <= 16) {
      suggestion += '中午时段气温较高，注意防晒补水。';
    } else {
      suggestion += '傍晚跑步有助于放松身心，注意安全。';
    }
    
    // 基于温度的建议
    if (temp < 5) {
      suggestion += '气温很低，建议充分热身，穿着保暖运动服。';
    } else if (temp < 10) {
      suggestion += '气温较低，建议穿着长袖运动服，热身时间不少于10分钟。';
    } else if (temp > 30) {
      suggestion += '天气较热，建议选择早晚凉爽时段跑步，注意防暑。';
    } else if (temp > 25) {
      suggestion += '气温较高，建议携带饮用水，适当降低运动强度。';
    } else {
      suggestion += '天气温度适宜，非常适合进行跑步训练。';
    }
    
    // 基于天气状况的建议
    var condition = weather.condition || '晴朗';
    if (condition.indexOf('雨') !== -1) {
      suggestion += '有降雨可能，建议室内运动或者携带防水装备。';
    } else if (condition.indexOf('雪') !== -1) {
      suggestion += '有降雪，建议选择室内运动确保安全。';
    } else if (condition.indexOf('雾') !== -1) {
      suggestion += '有雾霾，建议佩戴口罩或选择室内运动。';
    } else if (condition.indexOf('大风') !== -1) {
      suggestion += '风比较大，建议选择背风路线跑步。';
    }
    
    // 基于用户数据的建议
    var totalRuns = userStats.total_runs || 0;
    var weeklyDistance = parseFloat(userStats.weekly_distance) || 0;
    
    if (totalRuns === 0) {
      suggestion += '作为新手跑者，建议从3-5公里开始，循序渐进增加距离。';
    } else if (weeklyDistance < 10) {
      suggestion += '本周跑量相对较少，可以适当增加训练频率。';
    } else if (weeklyDistance > 40) {
      suggestion += '本周跑量较大，要注意合理安排休息。';
    }
    
    // 基于上次跑步时间的建议
    if (userStats.last_run_date) {
      var lastRunTime = new Date(userStats.last_run_date);
      var daysSinceLastRun = Math.floor((now - lastRunTime) / (1000 * 60 * 60 * 24));
      
      if (daysSinceLastRun > 3) {
        suggestion += '您已休息' + daysSinceLastRun + '天，建议今天恢复训练。';
      } else if (daysSinceLastRun === 0) {
        suggestion += '您今天已经跑步，建议适当休息恢复。';
      } else if (daysSinceLastRun === 1) {
        suggestion += '昨天刚跑过步，今天可以进行恢复性训练。';
      }
    }
    
    return suggestion || '根据当前条件，建议进行适度的跑步训练。';
  },

  // 修改后的页面加载顺序
  onLoad: function(options) {
    console.log('页面加载开始');
    
    var that = this;
    
    // 1. 先测试后端连接
    this.testBackendConnection();
    
    // 2. 加载本地数据
    this.loadRunningHistory();
    this.initLocation();
    
    // 3. 依次获取网络数据
    setTimeout(function() {
      that.getWeatherInfo().then(function() {
        // 天气获取成功后获取建议
        return that.getRunningSuggestion();
      }).catch(function(err) {
        console.error('数据加载失败:', err);
        that.useFallbackData();
      });
    }, 500);
    
  
    setTimeout(function() {
      that.calculateScrollHeight();
      that.calculateWeeklyStats();
      console.log('页面加载完成');
    }, 100);
  },

  // 使用备用数据
  useFallbackData: function() {
    console.log('使用备用数据');
    this.useDefaultWeatherData();
    this.useFallbackSuggestion();
  },

  // 修改getWeatherInfo为Promise形式
  getWeatherInfo: function() {
    var that = this;
    
    return new Promise(function(resolve, reject) {
      that.setData({ isLoadingWeather: true });
      
      wx.request({
        url: app.globalData.apiBase + '/api/weather',
        method: 'GET',
        data: { location: '北京' },
        header: {
          'Content-Type': 'application/json',
          'ngrok-skip-browser-warning': 'true'
        },
        success: function(res) {
          if (res.statusCode === 200 && res.data.success) {
            var weatherData = res.data.weather;
            var suitability = that.calculateRunningSuitability(weatherData);
            
            that.setData({
              weatherData: weatherData,
              runningSuitability: suitability,
              isLoadingWeather: false
            });
            
            console.log('天气数据获取成功');
            resolve(weatherData);
          } else {
            that.useDefaultWeatherData();
            reject(new Error('获取天气信息失败'));
          }
        },
        fail: function(err) {
          that.useDefaultWeatherData();
          reject(err);
        }
      });
    });
  },

  // 修改getRunningSuggestion为Promise形式
  getRunningSuggestion: function() {
    var that = this;
    
    return new Promise(function(resolve, reject) {
      that.setData({ isLoadingSuggestion: true });
      
      var requestData = {
        weather: that.data.weatherData || {},
        user_stats: that.calculateUserStats(),
        location: {
          city: '北京',
          latitude: that.data.currentLocation.latitude,
          longitude: that.data.currentLocation.longitude
        }
      };
      
      wx.request({
        url: app.globalData.apiBase + '/api/running-suggestion',
        method: 'POST',
        data: requestData,
        header: {
          'Content-Type': 'application/json',
          'ngrok-skip-browser-warning': 'true'
        },
        success: function(res) {
          if (res.statusCode === 200 && res.data.success) {
            that.setData({
              runningSuggestion: res.data.suggestion,
              isLoadingSuggestion: false
            });
            
            console.log('跑步建议获取成功');
            resolve(res.data.suggestion);
          } else {
            that.useFallbackSuggestion();
            reject(new Error('获取跑步建议失败'));
          }
        },
        fail: function(err) {
          that.useFallbackSuggestion();
          reject(err);
        }
      });
    });
  },

  // 初始化定位
  initLocation: function() {
    var that = this;
    
    wx.getLocation({
      type: 'gcj02',
      success: function(res) {
        that.setData({
          currentLocation: {
            latitude: res.latitude,
            longitude: res.longitude
          }
        });
      },
      fail: function(err) {
        console.error('获取位置失败:', err);
        that.useDefaultLocation();
      }
    });
  },

  // 使用默认位置
  useDefaultLocation: function() {
    this.setData({
      currentLocation: {
        latitude: 39.9042,
        longitude: 116.4074
      }
    });
  },

  // 开始跑步
  startRunning: function() {
    var that = this;
    
    wx.authorize({
      scope: 'scope.userLocation',
      success: function() {
        that.startRunningProcess();
      },
      fail: function() {
        wx.showModal({
          title: '需要位置权限',
          content: '请授权位置权限以记录跑步轨迹',
          success: function(res) {
            if (res.confirm) wx.openSetting();
          }
        });
      }
    });
  },

  startRunningProcess: function() {
    var startTime = Date.now();
    this.setData({
      isRunning: true,
      isPaused: false,
      startTime: startTime,
      runningData: { distance: 0, duration: '00:00', pace: '0', cadence: 0, calories: 0, steps: 0, avgPace: 0, avgCadence: 0 },
      pathPoints: [],
      pathPolyline: [{ points: [], color: '#007AFF', width: 4, dottedLine: false }],
      totalSeconds: 0,
      stepCount: 0,
      lastStepTime: 0
    });

    this.startTimer();
    this.startLocationUpdate();

    wx.showToast({ title: '开始跑步', icon: 'success' });
  },

  // 开始计时器
  startTimer: function() {
    var that = this;
    this.data.timer = setInterval(function() {
      if (that.data.isRunning && !that.data.isPaused) {
        var totalSeconds = that.data.totalSeconds + 1;
        var duration = that.formatTime(totalSeconds);
        var distance = that.data.runningData.distance;
        var pace = distance > 0 ? (totalSeconds / 60 / distance).toFixed(1) : '0';
        
        that.setData({
          totalSeconds: totalSeconds,
          'runningData.duration': duration,
          'runningData.pace': pace
        });

        if (distance > 0) {
          that.setData({
            'runningData.avgPace': (totalSeconds / 60 / distance).toFixed(1)
          });
        }
      }
    }, 1000);
  },

  // 开始位置更新
  startLocationUpdate: function() {
    var that = this;
    wx.startLocationUpdate({
      success: function() {
        wx.onLocationChange(function(res) {
          if (that.data.isRunning && !that.data.isPaused) {
            that.updateRunningPath(res);
          }
        });
      },
      fail: function(err) {
        console.error('开始位置更新失败:', err);
        wx.showToast({ title: '位置更新失败', icon: 'none' });
      }
    });
  },

  // 更新跑步路径
  updateRunningPath: function(location) {
    var newPoint = { latitude: location.latitude, longitude: location.longitude };
    var pathPoints = this.data.pathPoints.concat([newPoint]);
    var pathPolyline = [{
      points: pathPoints.map(function(point) {
        return { latitude: point.latitude, longitude: point.longitude };
      }),
      color: '#007AFF',
      width: 4,
      dottedLine: false
    }];

    var distance = this.data.runningData.distance;
    if (pathPoints.length > 1) {
      var lastPoint = pathPoints[pathPoints.length - 2];
      var delta = this.calculateDistance(lastPoint.latitude, lastPoint.longitude, newPoint.latitude, newPoint.longitude);
      distance += delta;
    }

    this.setData({
      currentLocation: newPoint,
      pathPoints: pathPoints,
      pathPolyline: pathPolyline,
      'runningData.distance': parseFloat(distance.toFixed(2))
    });
  },

  // 计算两点间距离
  calculateDistance: function(lat1, lng1, lat2, lng2) {
    var R = 6371000;
    var dLat = (lat2 - lat1) * Math.PI / 180;
    var dLng = (lng2 - lng1) * Math.PI / 180;
    var a = Math.sin(dLat/2) * Math.sin(dLat/2) +
            Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
            Math.sin(dLng/2) * Math.sin(dLng/2);
    var c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    return R * c / 1000;
  },

  // 暂停跑步
  pauseRunning: function() {
    this.setData({ isRunning: false, isPaused: true });
    wx.stopLocationUpdate();
    wx.showToast({ title: '已暂停', icon: 'success' });
  },

  // 停止跑步
  stopRunning: function() {
    clearInterval(this.data.timer);
    wx.stopLocationUpdate();
    this.saveRunningRecord();
    this.setData({ isRunning: false, isPaused: false, timer: null });
    wx.showToast({ title: '跑步结束', icon: 'success' });
  },

  // 保存跑步记录
  saveRunningRecord: function() {
    var record = {
      id: Date.now(),
      date: this.formatDate(new Date()),
      distance: this.data.runningData.distance,
      duration: this.data.runningData.duration,
      avgPace: this.data.runningData.avgPace,
      avgCadence: this.data.runningData.avgCadence,
      calories: this.data.runningData.calories,
      steps: this.data.runningData.steps,
      path: this.data.pathPoints
    };

    var history = [record].concat(this.data.runningHistory);
    this.setData({ runningHistory: history.slice(0, 10) });
    wx.setStorageSync('runningHistory', history.slice(0, 10));
    
    this.calculateWeeklyStats();
  },

  // 加载跑步历史
  loadRunningHistory: function() {
    var history = wx.getStorageSync('runningHistory') || [];
    this.setData({ runningHistory: history });
    this.calculateWeeklyStats();
  },

  // 格式化时间
  formatTime: function(totalSeconds) {
    var hours = Math.floor(totalSeconds / 3600);
    var minutes = Math.floor((totalSeconds % 3600) / 60);
    var seconds = totalSeconds % 60;
    
    if (hours > 0) {
      return hours.toString().padStart(2, '0') + ':' + minutes.toString().padStart(2, '0') + ':' + seconds.toString().padStart(2, '0');
    } else {
      return minutes.toString().padStart(2, '0') + ':' + seconds.toString().padStart(2, '0');
    }
  },

  // 格式化日期
  formatDate: function(date) {
    var year = date.getFullYear();
    var month = (date.getMonth() + 1).toString().padStart(2, '0');
    var day = date.getDate().toString().padStart(2, '0');
    var hours = date.getHours().toString().padStart(2, '0');
    var minutes = date.getMinutes().toString().padStart(2, '0');
    return year + '-' + month + '-' + day + ' ' + hours + ':' + minutes;
  },

  // 测试后端连接
  testBackendConnection: function() {
    var that = this;
    wx.request({
      url: app.globalData.apiBase + '/api/health',
      method: 'GET',
      header: {
        'Content-Type': 'application/json',
        'ngrok-skip-browser-warning': 'true'
      },
      success: function(res) {
        if (res.statusCode === 200) {
          console.log('后端连接测试成功');
        } else {
          console.error('后端连接测试失败');
        }
      },
      fail: function(err) {  
        console.error('后端连接测试失败:', err);
      }
    });
  },

  // 选择视频文件
  chooseVideo: function() {
    var that = this;
    wx.chooseMedia({
      count: 1,
      mediaType: ['video'],
      sourceType: ['album'],
      maxDuration: 60,
      camera: 'back',
      success: function(res) {
        var tempFilePath = res.tempFiles[0].tempFilePath; 
        that.setData({
          videoSrc: tempFilePath,
          analysisResult: null,
          processedVideoUrl: ''
        });
      },
      fail: function(err) {
        console.error('选择视频失败:', err);
        wx.showToast({ title: '选择视频失败', icon: 'none' });
      }
    });
  },

  // 开始录制视频
  startRecord: function() {
    var that = this;
    wx.chooseMedia({
      count: 1,
      mediaType: ['video'],
      sourceType: ['camera'],
      maxDuration: 60,
      camera: 'back',
      success: function(res) {
        var tempFilePath = res.tempFiles[0].tempFilePath;
        that.setData({
          videoSrc: tempFilePath,
          analysisResult: null,
          processedVideoUrl: ''
        });
      },
      fail: function(err) {
        console.error('录制视频失败:', err);
        wx.showToast({ title: '录制视频失败', icon: 'none' });
      }
    });
  },

  // 清除视频
  clearVideo: function() {
    this.setData({ 
      videoSrc: '',
      analysisResult: null,
      processedVideoUrl: ''
    });
  },

  // 上传视频进行分析
  uploadVideo: function() {
    var that = this;
    var videoSrc = this.data.videoSrc;
    
    if (!videoSrc) {
      wx.showToast({ title: '请先选择或录制视频', icon: 'none' });
      return;
    }
    
    this.setData({ isLoading: true });
    
    wx.uploadFile({
      url: app.globalData.apiBase + '/api/analyze',
      filePath: videoSrc,
      name: 'video',
      header: { 'Content-Type': 'multipart/form-data', 'ngrok-skip-browser-warning': 'true' },
      success: function(res) {
        if (res.statusCode === 200) {
          try {
            var data = JSON.parse(res.data);
            if (data.success) {
              that.setData({
                analysisResult: {
                  isGood: data.data.is_good,
                  details: data.data.details,
                  warnings: data.data.warnings
                }
              });
            } else {
              wx.showToast({ title: data.error || '分析失败', icon: 'none' });
            }
          } catch (e) {
            console.error('解析响应失败:', e);
            wx.showToast({ title: '解析响应失败', icon: 'none' });
          }
        } else {
          wx.showToast({ title: '上传失败，状态码: ' + res.statusCode, icon: 'none' });
        }
      },
      fail: function(err) {
        console.error('上传失败:', err);
        wx.showToast({ title: '上传失败，请重试', icon: 'none' });
      },
      complete: function() {
        that.setData({ isLoading: false });
      }
    });
  },
  
  // 视频错误处理
  onVideoError: function(e) {
    console.error('视频播放错误:', e.detail.errMsg);
    wx.showToast({
      title: '视频播放失败',
      icon: 'none'
    });
  }
})