# Custom Calendar for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
![Validate with hassfest](https://github.com/murianwind/custom_calendar/workflows/Validate%20with%20hassfest/badge.svg)

Home Assistant의 기존 캘린더 엔티티에서 특정 키워드를 필터링하여 새로운 전용 캘린더 엔티티를 생성해주는 통합 구성요소입니다. 출장, 휴가, 특정 업무 등 중요한 일정만 따로 추출하여 관리하고 싶을 때 유용합니다.

## ✨ 주요 기능

- **키워드 필터링**: 원본 달력에서 특정 단어가 포함된 일정만 추출하여 별도 엔티티로 관리.
- **엔티티 ID 커스텀**: 사용자가 입력한 고유 ID(`Unique ID`)를 기반으로 `calendar.my_id` 형식의 엔티티 자동 생성.
- **오프셋 알림 (Offset)**: 일정 제목에 `!!60`과 같이 표기하여 일정 시작 전 특정 시간에 `offset_reached` 상태 활성화.
- **상세 속성 제공**: `start_time`, `end_time`을 `YYYY-MM-DD HH:MM:SS` 형식으로 제공하여 자동화 및 대시보드 활용 용이.
- **실시간 설정 변경**: 통합 구성요소 화면의 **구성(Configure)** 버튼을 통해 검색어 및 미래 보기 범위를 즉시 수정 가능.
- **개별 엔티티 관리**: 기기 묶음 없이 각각의 통합 구성요소 항목으로 깔끔하게 관리.

## 🚀 설치 방법

### 방법 1: HACS (권장)

1. HACS > Integrations > 우측 상단 메뉴 > **Custom repositories** 선택.
2. 본 저장소 URL(`https://github.com/murianwind/custom_calendar`)을 입력하고 Category를 `Integration`으로 선택하여 추가합니다.
3. 목록에서 `Custom Calendar`를 찾아 설치합니다.
4. Home Assistant를 **재시작**합니다.

### 방법 2: 수동 설치

1. 본 저장소의 `custom_components/custom_calendar` 폴더를 다운로드합니다.
2. Home Assistant 설정 폴더(`config`) 내의 `custom_components` 폴더에 붙여넣습니다.
3. Home Assistant를 **재시작**합니다.

## ⚙️ 설정 방법

1. **설정 > 기기 및 서비스 > 통합 구성요소 추가**를 누릅니다.
2. `Custom Calendar`를 검색하여 선택합니다.
3. 다음 항목을 입력합니다:
    - **원본 달력**: 데이터를 가져올 기존 캘린더 엔티티 선택.
    - **이름**: 엔티티의 이름 (예: `출장 일정`).
    - **고유 ID**: 엔티티 ID로 사용될 고유값 (예: `company_trip` 입력 시 `calendar.company_trip` 생성).
    - **검색어**: 필터링할 키워드 (공백 시 모든 일정 가져옴).
    - **오프셋 구분자**: 오프셋 기능을 사용할 때 쓸 기호 (기본값: `!!`).
    - **미래 보기 범위**: 현재로부터 며칠간의 일정을 검색할지 설정 (최대 365일).

## 📊 엔티티 속성 (Attributes)

| 속성명 | 설명 | 예시 |
| :--- | :--- | :--- |
| `message` | 일정의 제목 | `일본 출장 !!60` |
| `all_day` | 종일 일정 여부 | `true` / `false` |
| `start_time` | 일정 시작 시간 | `2026-05-04 09:00:00` |
| `end_time` | 일정 종료 시간 | `2026-05-05 18:00:00` |
| `location` | 장소 정보 | `도쿄 본사` |
| `description` | 일정 상세 설명 | `프로젝트 미팅 건` |
| `offset_reached` | 오프셋 시간 도달 여부 | `true` / `false` |
| `friendly_name` | 현재 진행/예정된 일정 제목 | `일본 출장 !!60` |

## 🛠 자동화 예시 (Automation)

오프셋 기능을 활용하여 일정이 시작되기 1시간 전에 알림을 받는 예시입니다. (일정 제목에 `!!60` 포함 시)

```yaml
alias: "출장 1시간 전 알림"
trigger:
  - platform: state
    entity_id: calendar.company_trip
    attribute: offset_reached
    from: false
    to: true
action:
  - service: notify.mobile_app_my_phone
    data:
      title: "일정 알림"
      message: "{{ state_attr('calendar.company_trip', 'message') }} 일정이 곧 시작됩니다!"
