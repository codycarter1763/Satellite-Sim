using UnityEngine;

public class Follow_player : MonoBehaviour
{
    public Transform player;
    public Transform earth;

    public float distance = 15f;
    public float height = 8f;

private Vector3 previousPosition;
private bool hasPreviousPosition = false;
private Vector3 lastValidTangent = Vector3.right; // any safe non-zero default

void LateUpdate()
{
    if (player == null || earth == null)
        return;

    Vector3 radial = (player.position - earth.position).normalized;

    if (!hasPreviousPosition)
    {
        previousPosition = player.position;
        hasPreviousPosition = true;
        return;
    }

    Vector3 delta = player.position - previousPosition;

    // Only recompute direction when the satellite actually moved
    // this frame (i.e. a new telemetry packet arrived). Otherwise
    // keep using the last known-good tangent instead of collapsing
    // to a zero vector.
    if (delta.sqrMagnitude > 0.0001f)
    {
        Vector3 velocityDir = delta.normalized;
        lastValidTangent = Vector3.ProjectOnPlane(velocityDir, radial).normalized;
        previousPosition = player.position;
    }

    Vector3 tangent = lastValidTangent;

    Vector3 cameraPosition =
        player.position
        - tangent * distance
        + radial * height;

    transform.position = cameraPosition;

    Vector3 lookDirection = (player.position - cameraPosition).normalized;

    Vector3 earthDirection = (earth.position - player.position).normalized;
    Vector3 earthOnScreen = Vector3.ProjectOnPlane(earthDirection, lookDirection).normalized;
    Vector3 cameraUp = -earthOnScreen;

    if (lookDirection.sqrMagnitude > 0.001f && cameraUp.sqrMagnitude > 0.001f)
    {
        transform.rotation = Quaternion.LookRotation(lookDirection, cameraUp);
    }
}
}