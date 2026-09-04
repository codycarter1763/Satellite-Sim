using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

public class GroundTrack : MaskableGraphic
{
    [Header("Map")]
    [SerializeField] private RectTransform worldMap;
    [SerializeField] private RectTransform satelliteMarker;

    [Header("Trail")]
    [SerializeField] private float lineWidth = 4f;
    [SerializeField] private int maxTrailPoints = 500;

    [Header("Update")]
    [SerializeField] private float minimumPointSpacing = 5f;

    private readonly List<Vector2> trailPoints = new List<Vector2>();

    protected override void Awake()
    {
        base.Awake();
        raycastTarget = false;
        color = Color.white; // change if it blends into your map
    }

    public void SetPosition(float latitude, float longitude, float altitude)
{
    if (worldMap == null)
        return;

    Rect rect = worldMap.rect;

    // Longitude -> X (in worldMap's local space)
    float x = Mathf.Lerp(rect.xMin, rect.xMax, (longitude + 180f) / 360f);

    // Latitude -> Y (in worldMap's local space)
    float y = Mathf.Lerp(rect.yMin, rect.yMax, (latitude + 90f) / 180f);

    Vector2 mapPosition = new Vector2(x, y);

    // Move satellite marker — unchanged, this was already correct
    // since satelliteMarker shares worldMap's local coordinate space.
    if (satelliteMarker != null)
    {
        satelliteMarker.anchoredPosition = mapPosition;
    }

    // Convert into GroundTrack's own local space for the trail mesh,
    // since GroundTrack's pivot doesn't match worldMap's.
    Vector3 worldPoint = worldMap.TransformPoint(mapPosition);
    Vector2 trailPoint = rectTransform.InverseTransformPoint(worldPoint);

    // First point
    if (trailPoints.Count == 0)
    {
        trailPoints.Add(trailPoint);
        SetVerticesDirty();
        return;
    }

    Vector2 previous = trailPoints[trailPoints.Count - 1];

    // Don't add points too close together
    if (Vector2.Distance(trailPoint, previous) < minimumPointSpacing)
        return;

    // Handle ±180° longitude wrap
    // Note: comparing trailPoint.x jump against rect.width still works
    // since it's the same width, just offset — the *span* is unchanged
    // by a pivot difference, only the origin is.
    if (Mathf.Abs(trailPoint.x - previous.x) > rect.width * 0.5f)
    {
        trailPoints.Clear();
        trailPoints.Add(trailPoint);
        SetVerticesDirty();
        return;
    }

    trailPoints.Add(trailPoint);

    if (trailPoints.Count > maxTrailPoints)
        trailPoints.RemoveAt(0);

    SetVerticesDirty();
}

    public void ClearTrack()
    {
        trailPoints.Clear();
        SetVerticesDirty();
    }

    protected override void OnPopulateMesh(VertexHelper vh)
    {
        vh.Clear();

        if (trailPoints.Count < 2)
            return;

        for (int i = 0; i < trailPoints.Count - 1; i++)
        {
            Vector2 p1 = trailPoints[i];
            Vector2 p2 = trailPoints[i + 1];

            Vector2 direction = p2 - p1;

            if (direction.sqrMagnitude < 0.000001f)
                continue;

            direction.Normalize();

            Vector2 normal = new Vector2(-direction.y, direction.x) * (lineWidth * 0.5f);

            int index = vh.currentVertCount;

            vh.AddVert(p1 + normal, color, Vector2.zero);
            vh.AddVert(p1 - normal, color, Vector2.zero);
            vh.AddVert(p2 - normal, color, Vector2.zero);
            vh.AddVert(p2 + normal, color, Vector2.zero);

            vh.AddTriangle(index, index + 1, index + 2);
            vh.AddTriangle(index, index + 2, index + 3);
        }
    }
}