# 🚗 Driver Drowsiness Detection System  

<div align="center">

![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)  
![OpenCV](https://img.shields.io/badge/OpenCV-4.0+-green.svg)  
![License](https://img.shields.io/badge/License-MIT-yellow.svg)  
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey.svg)  

**An intelligent computer vision system to prevent drowsy driving**  

[Overview](#overview) • [Features](#features) • [Installation](#installation) • [Usage](#usage) • [Demo](#demo) • [Configuration](#configuration) • [Structure](#structure) • [Contributing](#contributing) • [License](#license)

</div>

---

## 📋 Overview  
A real-time computer vision application that monitors driver alertness using classical machine learning algorithms with OpenCV. Detects early signs of drowsiness and triggers alerts to prevent road accidents.

## ✨ Features  
- **Face & eye detection** using Haar Cascades  
- **Eye Aspect Ratio (EAR)** calculation for drowsiness detection  
- **Real-time audio/visual alerts**  
- **Adjustable sensitivity** with live calibration  
- **Data logging** for analysis  
- **Interactive controls** (keyboard shortcuts)  

## 🚀 Quick Start  

1. **Clone the repo**  
```bash
git clone https://github.com/your-username/driver-drowsiness-detection.git
cd driver-drowsiness-detection
```

2. **Install dependencies**  
```bash
pip install -r requirements.txt
```

3. **Run the system**  
```bash
python main.py
```

## ⚙️ Usage  
- **Sit 50–100 cm from the camera** with good front lighting  
- **System auto-calibrates** in the first 5 seconds  
- **Press Q to quit**, **R to reset**, **S to toggle sound**  
- **Adjust EAR threshold** with +/- keys  

## 🔧 Configuration  
Edit `CONFIG` in `main.py` to customize:  
- `EYE_AR_THRESHOLD`: Eye-closure sensitivity (default: 0.20)  
- `EYE_AR_CONSEC_FRAMES`: Frames for alert trigger (default: 10)  
- `ALARM_SOUND_PATH`: Custom alarm sound file  

## 📁 Project Structure  
```
driver-drowsiness-detection/
├── main.py              # Main script
├── requirements.txt     # Dependencies
├── sounds/              # Alarm sounds
├── logs/                # CSV logs
└── README.md
```

## 🤝 Contributing  
Contributions are welcome! Fork the repo and submit a pull request. See [Contributing](#contributing) for details.

## 📄 License  
MIT License. See [LICENSE](LICENSE) for full text.

## 👤 Author  
**omar badrani**  
- GitHub: https://github.com/omarbadrani  
- Email: omarbadrani770@gmail.com  

---

**⭐ If you find this useful, give it a star on GitHub!**  

**🚗 Drive safely — your safety matters!**
