import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { BalanceSnapshot } from '../entities/balance-snapshot.entity';
import { Trade } from '../entities/trade.entity';

@Injectable()
export class PerformanceService {
  constructor(
    @InjectRepository(Trade)
    private readonly tradesRepository: Repository<Trade>,
    @InjectRepository(BalanceSnapshot)
    private readonly balanceRepository: Repository<BalanceSnapshot>,
  ) {}

  async getAggregatePerformance() {
    const trades = await this.tradesRepository.find({
      where: { status: 'closed' },
    });

    const totalPnl = trades.reduce(
      (sum, trade) => sum + Number(trade.pnl ?? 0),
      0,
    );

    const latestBalance = await this.balanceRepository.find({
      order: { time: 'DESC' },
      take: 1,
    });

    return {
      totalPnl,
      closedTrades: trades.length,
      winRate: trades.length
        ? trades.filter((t) => Number(t.pnl ?? 0) > 0).length / trades.length
        : 0,
      latestBalance: latestBalance[0]
        ? {
            time: latestBalance[0].time,
            balance: Number(latestBalance[0].balance),
            nav: Number(latestBalance[0].nav ?? latestBalance[0].balance),
          }
        : null,
    };
  }

  async getBalanceHistory(limit = 500) {
    const rows = await this.balanceRepository.find({
      order: { time: 'ASC' },
      take: limit,
    });

    return rows.map((row) => ({
      time: row.time,
      balance: Number(row.balance),
      nav: Number(row.nav ?? row.balance),
    }));
  }
}
