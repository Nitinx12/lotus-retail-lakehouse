using System;
using System.Collections.Generic;

namespace LotusApi.Models;

public partial class PipelineRun
{
    public Guid RunId { get; set; }

    public string TaskName { get; set; } = null!;

    public string Status { get; set; } = null!;

    public DateTime StartedAt { get; set; }

    public DateTime? EndedAt { get; set; }

    public long? RowsIn { get; set; }

    public long? RowsOut { get; set; }

    public string? ErrorMessage { get; set; }
}
