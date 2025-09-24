from fastapi import FastAPI, HTTPException, Response
import requests
import os
from pathlib import Path

# 1. 初始化 FastAPI 应用（生产环境建议关闭 docs，或限制访问）
app = FastAPI(
    title="天气 SVG 图标服务",
    docs_url=None,  # 生产环境关闭自动生成的 API 文档（如需保留可改为 "/docs"）
    redoc_url=None
)

# 2. 配置参数（不变）
WEATHER_API_URL = "https://cloud-rest.lenovomm.com/cloud-weather/weather/localWeather"
SVG_STORAGE_DIR = "./weather"  # SVG 文件存放路径（确保与服务运行用户权限匹配）

# 3. 确保 SVG 目录存在（自动创建，避免手动操作）
Path(SVG_STORAGE_DIR).mkdir(parents=True, exist_ok=True)

# 4. 核心接口（根路径，对应域名直接访问）
@app.get("/", response_class=Response)
async def get_weather_svg():
    try:
        # 步骤1：请求天气 API 获取数据
        weather_response = requests.get(WEATHER_API_URL, timeout=10)
        weather_response.raise_for_status()  # 捕获 API 请求错误（如 404/500）
        weather_data = weather_response.json()

        # 步骤2：提取 weatherIndex 参数（严格按 API 返回格式解析）
        weather_index = weather_data.get("data", [{}])[0].get("current", {}).get("weatherIndex")
        if not weather_index:
            raise HTTPException(status_code=404, detail="未从天气 API 获取到 weatherIndex 参数")

        # 步骤3：验证 SVG 文件是否存在
        svg_filename = f"{weather_index}.svg"
        svg_full_path = os.path.join(SVG_STORAGE_DIR, svg_filename)
        if not os.path.exists(svg_full_path):
            raise HTTPException(
                status_code=404,
                detail=f"未找到对应 SVG 图标：{svg_filename}（路径：{svg_full_path}）"
            )

        # 步骤4：读取 SVG 内容并返回（确保浏览器内联显示，不触发下载）
        with open(svg_full_path, "rb") as f:
            svg_data = f.read()

        return Response(
            content=svg_data,
            media_type="image/svg+xml",  # 告诉浏览器这是 SVG 图像
            headers={
                "Content-Disposition": f"inline; filename={svg_filename}",  # 内联显示
                "Content-Length": str(os.path.getsize(svg_full_path))  # 优化加载体验
            }
        )

    # 异常处理（明确错误信息，便于排查）
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"天气 API 请求失败：{str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"服务器异常：{str(e)}")

# 5. 生产环境启动入口（用 uvicorn 绑定 80 端口）
if __name__ == "__main__":
    import uvicorn
    # 关键：绑定 80 端口（HTTP 标准端口），host=0.0.0.0 允许外部通过域名/IP 访问
    uvicorn.run(
        app="main:app",  # 格式：文件名:FastAPI实例名
        host="0.0.0.0",
        port=80,  # 绑定 HTTP 标准端口，浏览器访问无需加端口号
        workers=4,  # 生产环境建议设置 workers（通常为 CPU 核心数 * 2）
        reload=False  # 生产环境关闭热重载（避免性能损耗）
    )
