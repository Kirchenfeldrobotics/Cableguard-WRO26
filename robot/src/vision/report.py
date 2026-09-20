from comm_protocols.messages import VisionDetection, VisionTelemetry

# class name of the model => kind the protocol knows, in the class order of metadata.yaml.
# only the gradual metal loss is lma, everything else is a localised fault. unknown_defect is
# a real finding the model cannot name, lf keeps it out of the drop path in the backend
LABEL_TO_KIND = {
    "break":             "lf",
    "thunderbolt":       "lf",
    "wear":              "lma",
    "bird_caging":       "lf",
    "broken_wire":       "lf",
    "kink":              "lf",
    "mechanical_damage": "lf",
    "unknown_defect":    "lf",
}

# one detector result per frame, boxes normalised because the detection stream (main, 640x640)
# and the stream the webapp shows (lores, 640x480) do not share a resolution
def vision_telemetry(seq, cam, frame, found, captured_at, microsteps, distance_from_origin, inference_ms):
    h, w = frame.shape[:2]

    return VisionTelemetry(
        seq=seq,
        cam=cam,
        captured_at=captured_at,
        inference_ms=inference_ms,
        microsteps=microsteps,
        distance_from_origin=distance_from_origin,
        frame_w=w,
        frame_h=h,
        detections=[
            VisionDetection(
                label=det.label,
                kind=LABEL_TO_KIND.get(det.label),
                confidence=det.confidence,
                box=(det.box[0] / w, det.box[1] / h, det.box[2] / w, det.box[3] / h),
            )
            for det in found
        ],
    )
