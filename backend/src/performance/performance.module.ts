import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { Trade } from '../entities/trade.entity';
import { PerformanceController } from './performance.controller';
import { PerformanceService } from './performance.service';

@Module({
  imports: [TypeOrmModule.forFeature([Trade])],
  controllers: [PerformanceController],
  providers: [PerformanceService],
})
export class PerformanceModule {}
