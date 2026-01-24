class Device {
  constructor(alias, status, description) {
    this.alias = alias;
    this.status = status;
    this.description = description;
  }

  static fromJson(json) {
    return new Device(json.alias, json.status, json.description);
  }
}

export default Device;
