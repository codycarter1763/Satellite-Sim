using UnityEngine;

public class Follow_player : MonoBehaviour
{
    public Transform player;
    public Transform earth;

    public float distance = 15f;
    public float height = 8f;

    void LateUpdate()
    {
        if (player == null || earth == null)
            return;

        // Direction from Earth to satellite
        Vector3 radial =
            (player.position - earth.position).normalized;

        // Direction perpendicular to radial direction
        // for the current X-Y orbital plane.
        Vector3 tangent =
            new Vector3(-radial.y, radial.x, 0f).normalized;

        // ---------------------------------------------------------
        // CAMERA POSITION
        // ---------------------------------------------------------

        Vector3 cameraPosition =
            player.position
            - tangent * distance
            + Vector3.forward * height;

        transform.position = cameraPosition;

        // ---------------------------------------------------------
        // CAMERA LOOK DIRECTION
        // ---------------------------------------------------------

        Vector3 lookDirection =
            (player.position - cameraPosition).normalized;

        // ---------------------------------------------------------
        // KEEP EARTH AT THE BOTTOM OF THE SCREEN
        // ---------------------------------------------------------

        // Direction from satellite toward Earth
        Vector3 earthDirection =
            (earth.position - player.position).normalized;

        // Remove the component pointing toward the satellite
        // so we get Earth's direction across the camera plane.
        Vector3 earthOnScreen =
            Vector3.ProjectOnPlane(
                earthDirection,
                lookDirection
            ).normalized;

        // Camera "up" should point opposite Earth.
        // Therefore Earth appears at the bottom.
        Vector3 cameraUp =
            -earthOnScreen;

        // Apply rotation
        if (lookDirection.sqrMagnitude > 0.001f &&
            cameraUp.sqrMagnitude > 0.001f)
        {
            transform.rotation =
                Quaternion.LookRotation(
                    lookDirection,
                    cameraUp
                );
        }
    }
}