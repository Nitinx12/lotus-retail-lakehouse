using System;
using System.Collections.Generic;

namespace LotusApi.Models;

public partial class Alert
{
    public long AlertId { get; set; }

    public DateTime DetectedAt { get; set; }

    public string SourceTask { get; set; } = null!;

    public string Severity { get; set; } = null!;

    public string Message { get; set; } = null!;
}
