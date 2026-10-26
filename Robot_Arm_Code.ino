#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>
#include <math.h>

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();

float currentBase = 90;
float targetBase = 90;
float currentShoulder = 90;
float targetShoulder = 90;
float currentElbow = 90;
float targetElbow = 90;
float currentWristTilt = 90;
float targetWristTilt = 90;
float currentWristYaw = 90;
float targetWristYaw = 90;
float currentClaw = 90;
float targetClaw = 90;

unsigned long movementDurationMs = 3000;
unsigned long baseMovementDurationMs = 1000;
unsigned long previousMotionMillis = 0;
const unsigned long motionUpdateIntervalMs = 20;

long activeCommandId = -1;
bool commandPending = false;

int angleToPulse(int angle) {
  return map(angle, 0, 180, 150, 600);
}

bool readJsonInt(const String& json, const char* key, int& value) {
  String marker = String("\"") + key + "\"";
  int keyIndex = json.indexOf(marker);
  if (keyIndex == -1) {
    return false;
  }

  int colonIndex = json.indexOf(':', keyIndex + marker.length());
  if (colonIndex == -1) {
    return false;
  }

  value = json.substring(colonIndex + 1).toInt();
  return true;
}

bool syncPoseFromJson(const String& json) {
  int syncValue;
  if (!readJsonInt(json, "sync", syncValue) || syncValue != 1) {
    return false;
  }

  int base;
  int shoulder;
  int elbow;
  int wristtilt;
  int wristyaw;
  int claw;
  int commandId;

  bool valid =
      readJsonInt(json, "base", base) &&
      readJsonInt(json, "shoulder", shoulder) &&
      readJsonInt(json, "elbow", elbow) &&
      readJsonInt(json, "wristtilt", wristtilt) &&
      readJsonInt(json, "wristyaw", wristyaw) &&
      readJsonInt(json, "claw", claw) &&
      readJsonInt(json, "cmd_id", commandId);

  if (!valid) {
    Serial.println("ERROR:-1");
    return true;
  }

  currentBase = targetBase = constrain(base, 0, 180);
  currentShoulder = targetShoulder = constrain(shoulder, 0, 180);
  currentElbow = targetElbow = constrain(elbow, 0, 180);
  currentWristTilt = targetWristTilt = constrain(wristtilt, 10, 170);
  currentWristYaw = targetWristYaw = constrain(wristyaw, 10, 170);
  currentClaw = targetClaw = constrain(claw, 0, 180);

  pwm.setPWM(0, 0, angleToPulse((int)currentBase));

  int shoulderPulse = angleToPulse((int)currentShoulder);
  pwm.setPWM(2, 0, shoulderPulse);
  pwm.setPWM(3, 0, 750 - shoulderPulse);

  pwm.setPWM(4, 0, angleToPulse((int)currentElbow));
  pwm.setPWM(5, 0, angleToPulse((int)currentWristTilt));
  pwm.setPWM(7, 0, angleToPulse((int)currentWristYaw));
  pwm.setPWM(9, 0, angleToPulse((int)currentClaw));

  activeCommandId = -1;
  commandPending = false;
  previousMotionMillis = millis();

  Serial.print("READY:");
  Serial.println(commandId);
  return true;
}

float approachTarget(float current, float target, float maxStep) {
  float difference = target - current;

  if (difference > maxStep) {
    return current + maxStep;
  }
  if (difference < -maxStep) {
    return current - maxStep;
  }

  return target;
}

void writeServoIfChanged(float previousAngle, float currentAngle, uint8_t channel) {
  int previousRounded = (int)(previousAngle + 0.5f);
  int currentRounded = (int)(currentAngle + 0.5f);

  if (previousRounded != currentRounded) {
    pwm.setPWM(channel, 0, angleToPulse(currentRounded));
  }
}

void updateMotion(unsigned long now) {
  unsigned long elapsed = now - previousMotionMillis;
  if (elapsed < motionUpdateIntervalMs) {
    return;
  }
  previousMotionMillis = now;

  float baseMaxStep = 180.0f * elapsed / baseMovementDurationMs;
  float maxStep = 180.0f * elapsed / movementDurationMs;

  float oldBase = currentBase;
  float oldShoulder = currentShoulder;
  float oldElbow = currentElbow;
  float oldWristTilt = currentWristTilt;
  float oldWristYaw = currentWristYaw;
  float oldClaw = currentClaw;

  currentBase = approachTarget(currentBase, targetBase, baseMaxStep);
  currentShoulder = approachTarget(currentShoulder, targetShoulder, maxStep);
  currentElbow = approachTarget(currentElbow, targetElbow, maxStep);
  currentWristTilt = approachTarget(currentWristTilt, targetWristTilt, maxStep);
  currentWristYaw = approachTarget(currentWristYaw, targetWristYaw, maxStep);
  currentClaw = approachTarget(currentClaw, targetClaw, maxStep);

  writeServoIfChanged(oldBase, currentBase, 0);

  int oldShoulderPulse = angleToPulse((int)(oldShoulder + 0.5f));
  int shoulderPulse = angleToPulse((int)(currentShoulder + 0.5f));
  if (oldShoulderPulse != shoulderPulse) {
    pwm.setPWM(2, 0, shoulderPulse);
    pwm.setPWM(3, 0, 750 - shoulderPulse);
  }

  writeServoIfChanged(oldElbow, currentElbow, 4);
  writeServoIfChanged(oldWristTilt, currentWristTilt, 5);
  writeServoIfChanged(oldWristYaw, currentWristYaw, 7);
  writeServoIfChanged(oldClaw, currentClaw, 9);
}

bool allTargetsReached() {
  return fabs(currentBase - targetBase) < 0.01f &&
         fabs(currentShoulder - targetShoulder) < 0.01f &&
         fabs(currentElbow - targetElbow) < 0.01f &&
         fabs(currentWristTilt - targetWristTilt) < 0.01f &&
         fabs(currentWristYaw - targetWristYaw) < 0.01f &&
         fabs(currentClaw - targetClaw) < 0.01f;
}

void setup() {
  pwm.begin();
  pwm.setPWMFreq(50);

  Serial.begin(115200);
  Serial.setTimeout(50);

  // Do not command servo positions on startup.
  // Python must first sync to the arm's known physical pose.
  previousMotionMillis = millis();
}

void loop() {
  if (Serial.available()) {
    String json = Serial.readStringUntil('\n');

    if (syncPoseFromJson(json)) {
      return;
    }

    int value;
    bool hasTarget = false;

    if (readJsonInt(json, "base", value)) {
      targetBase = constrain(value, 0, 180);
      hasTarget = true;
    }
    if (readJsonInt(json, "shoulder", value)) {
      targetShoulder = constrain(value, 0, 180);
      hasTarget = true;
    }
    if (readJsonInt(json, "elbow", value)) {
      targetElbow = constrain(value, 0, 180);
      hasTarget = true;
    }
    if (readJsonInt(json, "wristtilt", value)) {
      targetWristTilt = constrain(value, 10, 170);
      hasTarget = true;
    }
    if (readJsonInt(json, "wristyaw", value)) {
      targetWristYaw = constrain(value, 10, 170);
      hasTarget = true;
    }
    if (readJsonInt(json, "claw", value)) {
      targetClaw = constrain(value, 0, 180);
      hasTarget = true;
    }
    if (readJsonInt(json, "duration_ms", value)) {
      movementDurationMs = constrain(value, 300, 30000);
    }
    if (readJsonInt(json, "base_duration_ms", value)) {
      baseMovementDurationMs = constrain(value, 300, 30000);
    }

    int commandId;
    if (hasTarget && readJsonInt(json, "cmd_id", commandId)) {
      activeCommandId = commandId;
      commandPending = true;
    }
  }

  updateMotion(millis());

  if (commandPending && allTargetsReached()) {
    Serial.print("DONE:");
    Serial.println(activeCommandId);
    commandPending = false;
  }
}