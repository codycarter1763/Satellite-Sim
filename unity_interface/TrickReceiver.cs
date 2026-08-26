using System;
using System.Net;
using System.Net.Sockets;
using System.Threading;
using UnityEngine;

public class TrickReceiver : MonoBehaviour
{
    private const int Port = 5005;

    private UdpClient udp;
    private Thread receiveThread;

    private Vector3 position;
    private Vector3 velocity;

    private readonly object stateLock = new object();

    void Start()
    {
        udp = new UdpClient(Port);

        receiveThread = new Thread(ReceiveData);
        receiveThread.IsBackground = true;
        receiveThread.Start();

        Debug.Log("Listening for Trick on UDP port " + Port);
    }

    void ReceiveData()
    {
        IPEndPoint endpoint =
            new IPEndPoint(IPAddress.Any, Port);

        while (true)
        {
            try
            {
                byte[] data = udp.Receive(ref endpoint);

                // 7 doubles:
                // time
                // position x,y,z
                // velocity x,y,z

                if (data.Length < 56)
                {
                    continue;
                }

                double time = BitConverter.ToDouble(data, 0);

                double x = BitConverter.ToDouble(data, 8);
                double y = BitConverter.ToDouble(data, 16);
                double z = BitConverter.ToDouble(data, 24);

                double vx = BitConverter.ToDouble(data, 32);
                double vy = BitConverter.ToDouble(data, 40);
                double vz = BitConverter.ToDouble(data, 48);

                lock (stateLock)
                {
                    position = new Vector3(
                        (float)x,
                        (float)y,
                        (float)z
                    );

                    velocity = new Vector3(
                        (float)vx,
                        (float)vy,
                        (float)vz
                    );
                }
            }
            catch
            {
                break;
            }
        }
    }

    void Update()
    {
        lock (stateLock)
        {
            transform.position = position;
        }
    }

    void OnApplicationQuit()
    {
        udp?.Close();
        receiveThread?.Abort();
    }
}