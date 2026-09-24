"use client";

import { api } from "@/lib/api/client";
import { useRobotLink } from "@/lib/robot/robot-link";
import { useApi } from "./use-api";

/**
 * The robot's settings as the server holds them, reloaded whenever anyone changes them.
 *
 * These are the values the server will hand the robot, not necessarily the ones it runs on:
 * a change only reaches a standing robot, so compare `version` with the `settings_version`
 * in the motion telemetry before telling the operator a setting is in force.
 */
export function useRobotSettings() {
  const { settingsVersion } = useRobotLink();
  return useApi(`settings:${settingsVersion}`, api.settings.get);
}
