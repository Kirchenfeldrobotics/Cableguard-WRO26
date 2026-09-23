/*
 * Values compiled into the robot (robot/src/app/main.py), mirrored here for the screens
 * that name them. The robot does not report its configuration, so these are copies: change
 * them here when they change there, and never show them as something the robot confirmed.
 */

/** Angle the camera ring parks at while the robot is open for a rope socket. */
export const OPEN_ANGLE_DEG = -20;

/** A distance reading below this opens the robot by itself, in metres. */
export const SOCKET_TRIGGER_M = 0.3;

/** Metres the robot drives from the socket before it closes again. */
export const SOCKET_CLEAR_M = 0.5;
