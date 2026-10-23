#include "motor_control.h"

#include "FastAccelStepper.h"

#include "apparatus_config.h"

static FastAccelStepperEngine engine = FastAccelStepperEngine();
static FastAccelStepper *stepper = NULL;
static bool motor_direction_forward = true;
static bool motor_start_pending = false;
static bool motor_stop_pending = false;
static int motor_step_interval_us = 1000;

void motor_control_init(void) {
  engine.init();
  stepper = engine.stepperConnectToPin(MOTOR_STEP_PIN);
  if (stepper) {
    stepper->setDirectionPin(MOTOR_DIR_PIN);
    stepper->setEnablePin(MOTOR_ENABLE_PIN);
    stepper->setAutoEnable(true);
  }
}

void motor_control_queue_start(uint8_t dir, uint16_t speed_us) {
  if (speed_us < MIN_STEP_INTERVAL_US) speed_us = MIN_STEP_INTERVAL_US;
  motor_step_interval_us = (int)speed_us;
  motor_direction_forward = (dir != 0);
  motor_start_pending = true;
}

void motor_control_queue_stop(void) {
  motor_stop_pending = true;
}

void motor_control_poll(void) {
  if (!stepper) return;

  if (motor_start_pending) {
    stepper->setSpeedInUs(motor_step_interval_us);
    stepper->setAcceleration(MOTOR_ACCELERATION_STEPS);
    if (motor_direction_forward) stepper->runForward();
    else stepper->runBackward();
    motor_start_pending = false;
  }

  if (motor_stop_pending) {
    stepper->stopMove();
    motor_stop_pending = false;
  }
}
