# 灵析 X1 上位机

一套用于课程设计的单通道虚拟示波与频谱分析上位机，替代原项目的 LabVIEW 程序。界面采用苹果软件风格的浅色半透明液态玻璃视觉，支持模拟数据和真实串口设备。

## 已实现功能

- 实时时域波形和 FFT 频谱
- 自动测量频率、峰峰值、交流 RMS、直流偏置和占空比
- 二至五次谐波与 THD
- 自动、正常和单次触发；上升沿与下降沿
- 正弦、方波、三角波和失真正弦模拟模式
- 二进制 CRC 协议与旧文本协议
- 丢帧、协议错误、断线和过载状态显示
- CSV 数据导出和 PNG 界面截图
- Windows 独立运行版本

## 直接运行

双击发布目录中的 `Lingxi-X1.exe`。程序默认进入模拟模式，不连接硬件也能完整演示。

源码运行：

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pip install -e .
.venv\Scripts\python.exe -m lingxi
```

## 连接硬件

1. 使用 USB 连接设备。
2. 点击“刷新”，选择对应 COM 口和波特率。
3. 关闭模拟模式，点击“连接设备”。
4. 固件优先使用 `PROTOCOL.md` 中的新二进制协议。

默认增益档位为 ×1、×5、×20、×100。真实板卡确定后，需要根据实际衰减电阻、放大倍数和标定结果修改 `main_window.py` 中的 `INPUT_SCALES`。每个数值表示该档位下 ADC 引脚电压换算回 BNC 输入电压的比例。

## 开发验证

```powershell
.venv\Scripts\python.exe -m pytest -q
```

## 打包

```powershell
.venv\Scripts\pyinstaller.exe --noconfirm --clean lingxi-x1.spec
```

生成结果位于 `dist\Lingxi-X1\Lingxi-X1.exe`。
