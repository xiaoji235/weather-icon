from fastapi import FastAPI, HTTPException, Response
import requests
import os
from pathlib import Path
import json

app = FastAPI(
    title="天气 SVG 图标服务",
    docs_url="/docs"
)

# 配置参数
WEATHER_API_URL = "https://cloud-rest.lenovomm.com/cloud-weather/weather/localWeather"
SVG_STORAGE_DIR = "./weather"
FIXED_IP = "27.213.62.20"  # 固定传递的IP地址

# 确保SVG目录存在
Path(SVG_STORAGE_DIR).mkdir(parents=True, exist_ok=True)

@app.get("/", response_class=Response)
async def get_weather_svg():
    try:
        # 1. 向天气API发送请求，传递固定IP参数
        params = {"ip": FIXED_IP}  # 传递固定IP
        weather_response = requests.get(
            WEATHER_API_URL,
            params=params,
            timeout=10
        )
        weather_response.raise_for_status()
        
        # 2. 处理API响应
        raw_response_text = weather_response.text
        print(f"天气API响应: {raw_response_text}")
        
        try:
            weather_data = weather_response.json()
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=500,
                detail=f"API返回非JSON格式: {str(e)}\n内容: {raw_response_text[:200]}"
            )
        
        # 3. 检查API返回状态码
        api_code = weather_data.get("code")
        if api_code != "10000":
            raise HTTPException(
                status_code=500,
                detail=f"天气API返回错误: {weather_data.get('message')}（code: {api_code}）"
            )
        
        # 4. 验证data字段
        data_list = weather_data.get("data")
        if not isinstance(data_list, list) or len(data_list) == 0:
            raise HTTPException(
                status_code=500,
                detail=f"data不是有效数组（类型: {type(data_list).__name__}）\n响应: {raw_response_text[:200]}"
            )
        
        # 5. 提取weatherIndex
        first_data = data_list[0]
        current_data = first_data.get("current", {})
        weather_index = current_data.get("weatherIndex")
        
        if not weather_index:
            raise HTTPException(status_code=404, detail="未找到weatherIndex参数")
        
        # 6. 返回SVG图标
        svg_filename = f"{weather_index}.svg"
        svg_full_path = os.path.join(SVG_STORAGE_DIR, svg_filename)
        
        if not Path(svg_full_path).exists():
            raise HTTPException(
                status_code=404,
                detail=f"未找到图标: {svg_filename}"
            )
        
        with open(svg_full_path, "rb") as f:
            svg_data = f.read()
        
        return Response(
            content=svg_data,
            media_type="image/svg+xml",
            headers={"Content-Disposition": f"inline; filename={svg_filename}"}
        )
    
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"API请求失败: {str(e)}")
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"服务器异常: {str(e)}")
