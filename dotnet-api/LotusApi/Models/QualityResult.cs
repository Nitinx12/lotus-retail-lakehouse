using System;
using System.Collections.Generic;

namespace LotusApi.Models;

public partial class QualityResult
{
    public Guid RunId { get; set; }

    public string SuiteName { get; set; } = null!;

    public decimal? SuccessPercent { get; set; }

    public int FailedExpectations { get; set; }

    public DateTime CheckedAt { get; set; }
}
