# 灵析 X1 串口协议

## 采样数据帧

所有多字节整数使用小端序。

| 字段 | 字节数 | 内容 |
|---|---:|---|
| Magic | 2 | `A5 5A` |
| Version | 1 | `01` |
| Type | 1 | `01`，采样帧 |
| Sequence | 2 | 递增帧序号 |
| SampleRate | 4 | 实际采样率，Sa/s |
| SampleCount | 2 | 采样点数量 |
| GainCode | 1 | 0、1、2、3 对应四档增益 |
| Coupling | 1 | 0 为 DC，1 为 AC |
| Flags | 2 | bit0 表示输入过载 |
| AdcBits | 1 | ADC 有效位数 |
| Reserved | 1 | 固定为 0 |
| VrefmV | 2 | ADC 参考电压，mV |
| ZeroCode | 2 | 0V 输入对应码值 |
| Samples | 2N | N 个无符号 ADC 原始码值 |
| CRC16 | 2 | Version 至 Samples 的 CRC-16/MODBUS |

STM32 不需要把 ADC 数据转换成浮点数，直接发送 DMA 缓冲区中的无符号 16 位原始码值即可。

## 控制命令

上位机发送 ASCII 命令，以 `\n` 结束：

- `RUN`
- `STOP`
- `SINGLE`
- `GAIN 0` 至 `GAIN 3`
- `COUPLING AC` 或 `COUPLING DC`
- `RATE 100000`
- `DEPTH 4096`

固件执行成功回复 `OK\n`，不支持的命令回复 `ERR UNSUPPORTED\n`。

## 旧协议

旧文本协议格式：

```text
<Time00640+Fre00100+Amp0+DC+2048,2050,2047>
```

`Time` 是 64 MHz 采样定时器的周期计数值，`Amp` 是增益档位，最后部分是十进制 ADC 采样值。由于原 LabVIEW 压缩包不包含 STM32 固件，如果旧固件实际使用二进制采样载荷，应优先将固件改为新协议，或提供一段真实串口原始数据用于适配。
