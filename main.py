from flask import Flask, make_response, abort
import requests
import os

app = Flask(__name__)

# 配置参数
WEATHER_API_URL = "https://cloud-rest.lenovomm.com/cloud-weather/weather/localWeather"
SVG_STORAGE_DIR = "./weather"  # SVG文件存放路径

# 确保SVG目录存在
os.makedirs(SVG_STORAGE_DIR, exist_ok=True)

@app.route("/")
def get_weather_svg():
    try:
        # 1. 请求天气API获取数据
        weather_response = requests.get(WEATHER_API_URL, timeout=10)
        weather_response.raise_for_status()
        weather_data = weather_response.json()
        
        # 2. 提取weatherIndex参数
        weather_index = weather_data.get("data", [{}])[0].get("current", {}).get("weatherIndex")
        
        if not weather_index:
            return "未获取到weatherIndex参数", 404
        
        # 3. 构建SVG文件路径并检查是否存在
        svg_filename = f"{weather_index}.svg"
        svg_full_path = os.path.join(SVG_STORAGE_DIR, svg_filename)
        
        if not os.path.exists(svg_full_path):
            return f"未找到SVG图标：{svg_filename}（路径：{svg_full_path}）", 404
        
        # 4. 读取SVG文件内容并构建响应
        with open(svg_full_path, "rb") as f:
            svg_data = f.read()
        
        # 创建响应对象并设置正确的响应头
        response = make_response(svg_data)
        # 指定内容类型为SVG，让浏览器识别为可显示的图像
        response.headers["Content-Type"] = "image/svg+xml"
        # 设置为内联显示，而非下载
        response.headers["Content-Disposition"] = f"inline; filename={svg_filename}"
        # 设置文件大小，优化加载体验
        response.headers["Content-Length"] = str(os.path.getsize(svg_full_path))
        
        return response
    
    except requests.exceptions.RequestException as e:
        return f"天气API请求失败：{str(e)}", 500
    except Exception as e:
        return f"服务器错误：{str(e)}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
    