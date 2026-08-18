# Sony Camera Wi-Fi Remote Control

Python + PyQt 기반의 Sony 카메라 Wi-Fi 원격 제어 애플리케이션입니다.

## 기능

- Wi-Fi를 통한 Sony 카메라 연결 (PTP-IP 프로토콜)
- 라이브 프리뷰
- 단일 사진 촬영
- 카메라 상태 표시 (배터리 등)

## 요구 사항

- Python 3.10+
- PyQt5
- Sony 카메라 (Wi-Fi 원격 제어 지원 모델)

## 설치

```bash
pip install -r requirements.txt
```

## 사용 방법

### 1. 카메라 설정

1. Sony 카메라에서 **Wi-Fi** 기능을 활성화합니다.
2. **PC Remote** 또는 **스마트폰 연결** 모드를 선택합니다.
3. 카메라가 Wi-Fi AP 모드로 전환되면, PC를 해당 Wi-Fi에 연결합니다.

### 2. 애플리케이션 실행

```bash
python main.py
```

### 3. 카메라 연결

1. 카메라 IP 주소를 입력합니다 (일반적으로 `192.168.122.1` 또는 `10.0.0.1`)
2. **Connect** 버튼을 클릭합니다.
3. 연결 성공 시 카메라 상태가 표시됩니다.

### 4. 사진 촬영

- **CAPTURE** 버튼을 클릭하여 사진을 촬영합니다.
- 촬영된 사진은 지정된 폴더에 저장됩니다.

## 카메라 호환성

이 애플리케이션은 Sony Camera Remote SDK (CrSDK)의 PTP-IP 프로토콜을 기반으로 합니다.

### 지원 예상 모델

- Sony Alpha 시리즈 (A7, A9 등)
- Sony FX 시리즈 (FX3, FX30, FX6 등)
- Sony ZV 시리즈
- 기타 Wi-Fi 원격 제어 지원 모델

> **참고:** 모든 기능이 모든 카메라에서 동작하지 않을 수 있습니다.
> 카메라 펌웨어 버전에 따라 호환성이 달라질 수 있습니다.

## 파일 구조

```
sony_wifi_camera/
├── main.py           # PyQt GUI 애플리케이션
├── ptp_ip.py         # PTP-IP 프로토콜 구현
├── requirements.txt  # Python 의존성
└── README.md         # 이 파일
```

## 프로토콜 참고

- **PTP-IP**: Picture Transfer Protocol over IP (ISO 15740)
- **Sony SDIO**: Sony Device I/O Extensions
- 포트: 15740 (표준 PTP-IP 포트)

## 문제 해결

### 연결이 안 될 때

1. 카메라가 **PC Remote** 모드인지 확인
2. PC가 카메라의 Wi-Fi 네트워크에 연결되었는지 확인
3. 방화벽에서 포트 15740이 허용되었는지 확인
4. 카메라 IP 주소가 올바른지 확인 (보통 게이트웨이 주소)

### 촬영이 안 될 때

1. 카메라가 촬영 가능한 상태인지 확인 (메모리 카드 삽입, 배터리 충분)
2. 연결이 정상적으로 유지되고 있는지 확인

## 라이선스

이 프로젝트는 교육 및 개인 사용 목적으로 제작되었습니다.
Sony Camera Remote SDK의 프로토콜을 참고하여 구현되었습니다.

## 참고 자료

- [Sony Camera Remote SDK](https://developer.sony.com/)
- [PTP-IP Specification](https://www.cipa.jp/std/documents/e/DC-X005.pdf)
