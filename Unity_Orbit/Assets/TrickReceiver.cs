using System;
using System.Net;
using System.Net.Sockets;
using System.Threading;
using UnityEngine;

public class TrickReceiver : MonoBehaviour
{
    [Header("UDP")]
    [SerializeField] private int port = 5005;

    [Header("Object")]
    [SerializeField] private Transform vehicle;

    [Header("Simulation Scale")]
    // 1 Unity unit = 1,000,000 meters
    // Earth radius:
    // 6,371,000 m * 0.000001 = 6.371 Unity units
    [SerializeField] private float metersToUnity = 0.000001f;

    [Header("Coordinate System")]
    // Initial JEOD Earth.inertial -> Unity mapping.
    // We can adjust this later if the orbit is rotated incorrectly.
    [SerializeField] private bool swapYZ = false;
    [SerializeField] private bool invertX = false;
    [SerializeField] private bool invertY = false;
    [SerializeField] private bool invertZ = false;

    [Header("Smoothing")]
    [SerializeField] private float positionSmooth = 20f;
    [SerializeField] private float rotationSmooth = 20f;

    // =========================================================
    // Packet format
    //
    // 7 doubles = 7 * 8 = 56 bytes
    //
    // Bytes:
    //   0  - 7   Position X
    //   8  - 15  Position Y
    //   16 - 23  Position Z
    //   24 - 31  Quaternion W
    //   32 - 39  Quaternion X
    //   40 - 47  Quaternion Y
    //   48 - 55  Quaternion Z
    // =========================================================

    private const int PACKET_SIZE = 56;

    private UdpClient udp;
    private Thread receiveThread;
    private volatile bool running;

    private readonly object stateLock = new object();

    // =========================================================
    // Current received state
    // =========================================================

    private Vector3 vehiclePosition;
    private Quaternion vehicleRotation;

    private bool hasData;
    private float debugTimer = 0f;

    // =========================================================
    // Start
    // =========================================================

    void Start()
    {
        try
        {
            udp = new UdpClient(port);

            running = true;

            receiveThread = new Thread(ReceiveData);
            receiveThread.IsBackground = true;
            receiveThread.Start();

            Debug.Log(
                $"Listening for Trick data on UDP port {port}"
            );

            Debug.Log(
                $"Simulation scale: {metersToUnity} Unity units/meter"
            );
        }
        catch (Exception e)
        {
            Debug.LogError(
                $"Failed to start UDP receiver: {e.Message}"
            );
        }
    }


    // =========================================================
    // Receive UDP data
    // =========================================================

    void ReceiveData()
    {
        IPEndPoint endpoint =
            new IPEndPoint(
                IPAddress.Any,
                port
            );

        while (running)
        {
            try
            {
                byte[] data =
                    udp.Receive(ref endpoint);


                // -------------------------------------------------
                // Validate packet size
                // -------------------------------------------------

                if (data.Length != PACKET_SIZE)
                {
                    Debug.LogWarning(
                        $"Expected {PACKET_SIZE} bytes, " +
                        $"received {data.Length}"
                    );

                    continue;
                }


                // =================================================
                // Vehicle Position
                // =================================================

                double vehicleX =
                    BitConverter.ToDouble(data, 0);

                double vehicleY =
                    BitConverter.ToDouble(data, 8);

                double vehicleZ =
                    BitConverter.ToDouble(data, 16);


                // =================================================
                // Vehicle Quaternion
                // =================================================

                double vehicleW =
                    BitConverter.ToDouble(data, 24);

                double vehicleQX =
                    BitConverter.ToDouble(data, 32);

                double vehicleQY =
                    BitConverter.ToDouble(data, 40);

                double vehicleQZ =
                    BitConverter.ToDouble(data, 48);


                // =================================================
                // Convert JEOD meters -> Unity units
                // =================================================

                float x =
                    (float)(vehicleX * metersToUnity);

                float y =
                    (float)(vehicleY * metersToUnity);

                float z =
                    (float)(vehicleZ * metersToUnity);


                // =================================================
                // Coordinate system conversion
                //
                // Initially this is:
                //
                // JEOD X -> Unity X
                // JEOD Y -> Unity Y
                // JEOD Z -> Unity Z
                //
                // The options below let us adjust the mapping
                // without changing the rest of the receiver.
                // =================================================

                if (swapYZ)
                {
                    float temp = y;
                    y = z;
                    z = temp;
                }

                if (invertX)
                    x = -x;

                if (invertY)
                    y = -y;

                if (invertZ)
                    z = -z;


                Vector3 newPosition =
                    new Vector3(
                        x,
                        y,
                        z
                    );


                // =================================================
                // Create Unity quaternion
                // =================================================

                Quaternion newRotation =
                    new Quaternion(
                        (float)vehicleQX,
                        (float)vehicleQY,
                        (float)vehicleQZ,
                        (float)vehicleW
                    );


                // -------------------------------------------------
                // Normalize quaternion
                // -------------------------------------------------

                newRotation.Normalize();


                // =================================================
                // Store received state
                // =================================================

                lock (stateLock)
                {
                    vehiclePosition = newPosition;
                    vehicleRotation = newRotation;

                    hasData = true;
                }
            }
            catch (SocketException)
            {
                if (running)
                {
                    Debug.LogError(
                        "UDP socket error."
                    );
                }
            }
            catch (Exception e)
            {
                if (running)
                {
                    Debug.LogError(
                        $"UDP receive error: {e.Message}"
                    );
                }
            }
        }
    }


    // =========================================================
    // Unity frame update
    // =========================================================

    void Update()
    {
        debugTimer += Time.deltaTime;

if (debugTimer >= 1.0f)
{
    debugTimer = 0f;

    lock (stateLock)
    {
        if (hasData)
        {
            Debug.Log(
                $"Satellite Position: " +
                $"X={vehiclePosition.x:F6}, " +
                $"Y={vehiclePosition.y:F6}, " +
                $"Z={vehiclePosition.z:F6}"
            );
        }
        else
        {
            Debug.Log("No Trick data received yet.");
        }
    }
}
        Vector3 pos;
        Quaternion rot;


        // ---------------------------------------------------------
        // Copy latest received state
        // ---------------------------------------------------------

        lock (stateLock)
        {
            if (!hasData)
            {
                return;
            }

            pos = vehiclePosition;
            rot = vehicleRotation;
        }
        float distance = pos.magnitude;

        Debug.Log($"Satellite distance from Unity origin: {distance}");


        // ---------------------------------------------------------
        // Calculate frame-rate independent smoothing
        // ---------------------------------------------------------

        float positionT =
            1f - Mathf.Exp(
                -positionSmooth *
                Time.deltaTime
            );

        float rotationT =
            1f - Mathf.Exp(
                -rotationSmooth *
                Time.deltaTime
            );


        // =========================================================
        // Vehicle
        // =========================================================

        if (vehicle != null)
        {
            vehicle.position =
                Vector3.Lerp(
                    vehicle.position,
                    pos,
                    positionT
                );

            vehicle.rotation =
                Quaternion.Slerp(
                    vehicle.rotation,
                    rot,
                    rotationT
                );
        }
    }


    // =========================================================
    // Shutdown
    // =========================================================

    void OnApplicationQuit()
    {
        running = false;

        try
        {
            udp?.Close();
        }
        catch
        {
            // Ignore shutdown errors.
        }

        try
        {
            if (receiveThread != null &&
                receiveThread.IsAlive)
            {
                receiveThread.Join(500);
            }
        }
        catch
        {
            // Ignore shutdown errors.
        }
    }
}