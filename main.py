from fastapi import FastAPI, HTTPException, Response, Request
import requests
import os
from pathlib import Path
import json
from typing import Dict

app = FastAPI(
    title="动态IP存储与天气服务",
    docs_url="/docs"
)

# 配置参数
WEATHER_API_URL = "https://cloud-rest.lenovomm.com/cloud-weather/weather/localWeather"
SVG_STORAGE_DIR = "./weather"

# 内存存储：保存用户IP（key为会话标识，这里简化为直接存储最新IP）
# 生产环境可改用Redis等持久化存储
ip_storage: Dict[str, str] = {"latest_ip": None}  # 存储结构：{"latest_ip": "用户IP"}

# 确保SVG目录存在
Path(SVG_STORAGE_DIR).mkdir(parents=True, exist_ok=True)

@app.get("/")
async def get_weather_svg(request: Request):
    try:
        # 1. 获取用户真实IP并存储到ip_storage中
        # 从代理头获取（Vercel等平台）
        client_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        # 若获取不到则用客户端主机
        if not client_ip:
            client_ip = request.client.host
        
        # 将用户IP存入存储中（覆盖最新IP）
        ip_storage["latest_ip"] = client_ip
        print(f"已更新最新用户IP: {client_ip}")  # 调试日志

        # 2. 从存储中获取IP（即用户刚刚访问时存入的IP）
        fixed_ip = ip_storage["latest_ip"]
        if not fixed_ip:
            raise HTTPException(status_code=500, detail="未获取到用户IP")

        # 3. 调用天气API，传递用户IP
        params = {"ip": fixed_ip}
        weather_response = requests.get(
            WEATHER_API_URL,
            params=params,
            timeout=10
        )
        weather_response.raise_for_status()

        # 4. 处理API响应（后续逻辑与之前一致）
        raw_response_text = weather_response.text
        print(f"天气API响应: {raw_response_text}")

        try:
            weather_data = weather_response.json()
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=500,
                detail=f"API返回非JSON格式: {str(e)}\n内容: {raw_response_text[:200]}"
            )

        api_code = weather_data.get("code")
        if api_code != "10000":
            raise HTTPException(
                status_code=500,
                detail=f"天气API错误: {weather_data.get('message')}（code: {api_code}）"
            )

        data_list = weather_data.get("data")
        if not isinstance(data_list, list) or len(data_list) == 0:
            raise HTTPException(
                status_code=500,
                detail=f"data不是有效数组（类型: {type(data_list).__name__}）"
            )

        first_data = data_list[0]
        current_data = first_data.get("current", {})
        weather_index = current_data.get("weatherIndex")

        if not weather_index:
            raise HTTPException(status_code=404, detail="未找到weatherIndex参数")

        # 5. 返回SVG图标
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
