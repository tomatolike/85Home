class RobotStatus {
  constructor(key, value) {
    this.key = key;
    this.value = value;
  }

  static fromJson(json) {
    return new RobotStatus(json.key, json.value);
  }
}

export default RobotStatus;
