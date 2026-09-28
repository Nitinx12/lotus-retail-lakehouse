// controller tests over an in memory gold context
using LotusApi.Controllers;
using LotusApi.Data;
using LotusApi.Models;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

namespace LotusApi.Tests;

public class MartsControllerTests
{
    // test twin that keys the mart so the in memory store can seed it
    private sealed class TestGoldContext(DbContextOptions<LotusGoldContext> options)
        : LotusGoldContext(options)
    {
        protected override void OnModelCreating(ModelBuilder modelBuilder)
        {
            base.OnModelCreating(modelBuilder);
            modelBuilder.Entity<RevenueByStoreMonth>()
                .HasKey(r => new { r.StoreId, r.Month });
        }
    }

    private static LotusGoldContext SeedContext()
    {
        var options = new DbContextOptionsBuilder<LotusGoldContext>()
            .UseInMemoryDatabase($"lotus_test_{Guid.NewGuid()}")
            .Options;
        var db = new TestGoldContext(options);
        db.RevenueByStoreMonths.AddRange(
            new RevenueByStoreMonth { StoreId = 1, Month = "2024-01", Revenue = 100m },
            new RevenueByStoreMonth { StoreId = 2, Month = "2024-01", Revenue = 50m });
        db.SaveChanges();
        return db;
    }

    [Fact]
    public async Task RevenueByStoreMonth_returns_all_rows()
    {
        using var db = SeedContext();
        var result = await new MartsController(db).RevenueByStoreMonth(null, null);
        var ok = Assert.IsType<OkObjectResult>(result);
        Assert.Equal(2, ((List<RevenueByStoreMonth>)ok.Value!).Count);
    }

    [Fact]
    public async Task RevenueByStoreMonth_filters_by_store()
    {
        using var db = SeedContext();
        var result = await new MartsController(db).RevenueByStoreMonth(1, null);
        var ok = Assert.IsType<OkObjectResult>(result);
        var rows = (List<RevenueByStoreMonth>)ok.Value!;
        Assert.Single(rows);
        Assert.Equal(100m, rows[0].Revenue);
    }
}
