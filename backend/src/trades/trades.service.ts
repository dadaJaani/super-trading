import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Signal } from '../entities/signal.entity';
import { Trade } from '../entities/trade.entity';

@Injectable()
export class TradesService {
  constructor(
    @InjectRepository(Trade)
    private readonly tradesRepository: Repository<Trade>,
    @InjectRepository(Signal)
    private readonly signalsRepository: Repository<Signal>,
  ) {}

  findTradesByBot(botId: string): Promise<Trade[]> {
    return this.tradesRepository.find({
      where: { botId },
      order: { openTime: 'DESC' },
    });
  }

  findSignalsByBot(botId: string): Promise<Signal[]> {
    return this.signalsRepository.find({
      where: { botId },
      order: { time: 'DESC' },
    });
  }
}
