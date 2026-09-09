using UnityEngine;

public class EarthRotation : MonoBehaviour
{
    private const double EarthRotationRate =
        7.2921151467e-5;

    private double simulationTime = 0.0;

    private Vector3 initialEulerAngles;

    void Start()
    {
        // Save the model's existing orientation.
        // X and Z will remain constant.
        initialEulerAngles = transform.localEulerAngles;
    }

    public void SetSimulationTime(double time)
    {
        simulationTime = time;
    }

    void Update()
    {
        double angle =
            simulationTime * EarthRotationRate;

        float angleDegrees =
            (float)(angle * Mathf.Rad2Deg);

        Vector3 rotation = new Vector3(
            initialEulerAngles.x,
            initialEulerAngles.y - angleDegrees,
            initialEulerAngles.z
        );

        transform.localEulerAngles = rotation;
    }
}