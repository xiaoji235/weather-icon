from fastapi import FastAPI, HTTPException, Response, Request
import requests
import os
from pathlib import Path
import json

app = FastAPI(
    title="自动获取IP的天气SVG图标服务",
    docs_url="/docs"
)

# 配置参数
WEATHER_API_URL = "https://cloud-rest.lenovomm.com/cloud-weather/weather/localWeather"
SVG_STORAGE_DIR = "./weather"

# 确保SVG目录存在
Path(SVG_STORAGE_DIR).mkdir(parents=True, exist_ok=True)

def get_client_ip(request: Request) -> str:
    """获取客户端真实IP地址的工具函数"""
    # 从代理头获取（适用于Vercel等部署环境）
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        # X-Forwarded-For格式通常为：客户端IP, 代理1IP, 代理2IP...
        return x_forwarded_for.split(",")[0].strip()
    
    # 从X-Real-IP头获取（部分代理使用）
    x_real_ip = request.headers.get("X-Real-IP")
    if x_real_ip:
        return x_real_ip
    
    # 直接获取客户端IP（本地环境）
    if request.client:
        return request.client.host
    
    # 所有方式都获取失败时返回默认值
    return "127.0.0.1"

@app.get("/", response_class=Response)
async def get_weather_svg(request: Request):
    try:
        # 1. 获取客户端真实IP
        client_ip = get_client_ip(request)
        print(f"获取到的客户端IP: {client_ip}")
        
        # 2. 向天气API发送请求，传递IP参数
        params = {"ip": client_ip}  # 假设API接受ip参数
        weather_response = requests.get(
            WEATHER_API_URL,
            params=params,
            timeout=10
        )
        weather_response.raise_for_status()
        
        # 3. 处理API响应
        raw_response_text = weather_response.text
        print(f"天气API响应({client_ip}): {raw_response_text}")
        
        try:
            weather_data = weather_response.json()
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=500,
                detail=f"API返回非JSON格式: {str(e)}\n内容: {raw_response_text[:200]}"
            )
        
        # 4. 检查API返回状态码
        api_code = weather_data.get("code")
        if api_code != "10000":
            raise HTTPException(
                status_code=500,
                detail=f"天气API错误({client_ip}): {weather_data.get('message')}（code: {api_code}）"
            )
        
        # 5. 验证data字段
        data_list = weather_data.get("data")
        if not isinstance(data_list, list) or len(data_list) == 0:
            raise HTTPException(
                status_code=500,
                detail=f"{client_ip}的data不是有效数组（类型: {type(data_list).__name__}）"
            )
        
        # 6. 提取weatherIndex
        first_data = data_list[0]
        current_data = first_data.get("current", {})
        weather_index = current_data.get("weatherIndex")
        
        if not weather_index:
            raise HTTPException(status_code=404, detail=f"{client_ip}未找到weatherIndex参数")
        
        # 7. 返回SVG图标
        svg_filename = f"{weather_index}.svg"
        svg_full_path = os.path.join(SVG_STORAGE_DIR, svg_filename)
        
        if not Path(svg_full_path).exists():
            raise HTTPException(
                status_code=404,
                detail=f"未找到{weather_index}.svg（IP: {client_ip}）"
            )
        
        with open(svg_full_path, "rb") as f:
            svg_data = f.read()
        
        return Response(
            content=svg_data,
            media_type="image/svg+xml",
            headers={"Content-Disposition": f"inline; filename={client_ip}_{svg_filename}"}
        )
    
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"API请求失败({client_ip}): {str(e)}")
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"服务器异常: {str(e)}")
